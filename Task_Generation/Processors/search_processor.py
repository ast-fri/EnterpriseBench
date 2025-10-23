import json
import logging
import random
from itertools import combinations
# Set up logger
logger = logging.getLogger(__name__)

class SearchProcessor:
    def __init__(self):
        """
        Initializes the KQADataProcessor with data sources configuration.
        
        Args:
            data_sources (dict, optional): Dictionary containing data source configurations.
        """

    
    def get_filtered_data(self, id, source_paths):
        """
        Retrieves a comprehensive dictionary of raw items, entities, and triples filtered by chain and employee ID.
        
        Args:
            chain (str): Chain of data sources separated by '->'
            emp_id (str): Employee ID to filter data
            source_path (str): Path to the raw source data
            entity_source_path (str): Path to the entity source JSON file
            triple_source_path (str): Path to the triple source JSON file
            
        Returns:
            dict: Dictionary containing:
                - raw_items: Original data items matching the filter criteria
                - entities: Entities from the matched items
                - triples: Triples from the matched items
                
        Raises:
            ValueError: If required parameters are invalid
            FileNotFoundError: If required files cannot be found
            json.JSONDecodeError: If JSON files are malformed
        """
        try:
            # print(id)
            # print(source_paths)
            # Validate input parameters
            conv_source= ["Engineering Team Conversations", "Finance Team Conversations", "Management Team Conversations", "Sales Team Conversations", "HR Conversations", "SDE Conversations", "Customer Support Chats"]
            workspace = ["GitHub"]
            employee = ["Employee Data"]
            it_tickets = ["IT Service Management"]
            
            if not id:
                raise ValueError("Employee ID must be provided")
                
            result = {}
    
            # Step 1: Get entities based on employee ID
            for source in list(source_paths.keys()):
                # # print(source)
                result[source]=[]
                with open(source_paths[source], 'r') as f:
                    document_items = json.load(f)
                if source == "Enterprise Mail System":
                    filtered_items = [
                        item for idx, item in enumerate(document_items)
                        if id == item["sender"]["emp_id"] or id == item["recipient"]["emp_id"]
                    ]
                elif source == "Product Sentiment":
                    filtered_items = [
                        item for idx, item in enumerate(document_items)
                        if id == item["customer_id"] or id ==item["product_id"]
                    ]
                elif source == "Sales":
                    filtered_items = [
                        item for idx, item in enumerate(document_items)
                        if id == item["customer_id"] or id ==item["product_id"]
                    ]   
                elif source in conv_source:
                    filtered_items = [
                        item for item in document_items
                        if id == item["metadata"]["emp1_id"] or id == item["metadata"]["emp2_id"]
                    ]
                elif source in workspace:
                    filtered_items = [
                        item for item in document_items
                        if id == item["emp_id"]
                    ]
                elif source in employee:
                    filtered_items = [
                        item for item in document_items
                        if id == item["emp_id"]
                    ]
                elif source in it_tickets:
                    filtered_items = [
                        item for item in document_items
                        if id == item["emp_id"]
                    ]
                else:
                    filtered_items = []
            for source in list(source_paths.keys()):
                result[source] = filtered_items[random.randint(0, len(filtered_items)-1)] if len(filtered_items)>0 else []
            return result
            
        except Exception as e:
            logger.error(f"Error in get_filtered_data: {str(e)}")
            raise
    def get_employee_persona(self, ids):
        # # print(ids)
        persona = []
            # Process each available source
        with open("/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Human_Resource_Management/Employees/employees.json", 'r') as f:
            employees = json.load(f)
        for emp in employees:
            if(emp["emp_id"] in ids):
                persona.append(emp)
        return persona
   

    def load_json(self, file, dataset_name, task_domain):

        with open(file, 'r') as f:
            data = json.load(f)

        # print(task_domain)
        if dataset_name == "Employee Data":
            domain_map = {
                "hr": "HR",
                "swe": "Engineering",
                "sales": "Sales",
                "manag": "Management",
                "it": "Information Technology"
            }
            # Map the task_domain to the appropriate domain string
            mapped_domain = domain_map.get(task_domain)
            if mapped_domain:
                # print("mapping")
                # Filter data entries whose category matches the mapped domain
                data = [d for d in data if d.get("category") == mapped_domain]
                # print(len(data))
        random.shuffle(data)
        return data
        

    def find_common_keys(self, data1, data2, data1_name, data2_name):
        if not data1 or not data2:
            return set()
        special_types = ["Enterprise Mail System", "Conversations", "IT Service Management"]

        data1_keys = set(data1[0].keys())
        data2_keys = set(data2[0].keys())

        # Define equivalent keys group
        emp_key_group = {"emp_id", "sender_emp_id", "recipient_emp_id", "raised_by_emp_id"}

        if data1_name in special_types or data2_name in special_types:
            # Check if any key from group present in data1 and any in data2
            if emp_key_group.intersection(data1_keys) and emp_key_group.intersection(data2_keys):
                # Return the whole group to signal equivalence
                return emp_key_group
            else:
                # No matching emp keys, return empty set
                return set()

        # For non-special datasets, normal intersection
        return data1_keys.intersection(data2_keys)

    def filter_data(self, data, filters):
        # Filter data list by matching all key-value pairs in filters
        return [item for item in data if all(item.get(k) == v for k, v in filters.items())]

    def build_pair_keys(self, datasets, dataset_names):
        # Build dictionary mapping pairs of dataset indices to their common keys
        pair_keys = {}
        n = len(datasets)
        for i, j in combinations(range(n), 2):
            common = self.find_common_keys(datasets[i], datasets[j], dataset_names[i], dataset_names[j])
            if common:
                pair_keys[(i, j)] = common
        return pair_keys
    def employee_ids_match(self, entry1, entry2):
        emp_keys = {"emp_id", "sender_emp_id", "recipient_emp_id", "raised_by_emp_id"}
        ids1 = {entry1.get(k) for k in emp_keys if k in entry1}
        ids2 = {entry2.get(k) for k in emp_keys if k in entry2}
        # If ids1 and ids2 have any intersection, treat as match
        return bool(ids1.intersection(ids2))
    def consistent_with_selections(self, candidate, selected, pair_keys, idx, datasets, dataset_name):
        # Check if candidate at index idx is consistent with all currently selected candidates
        for other_idx, other_sel in enumerate(selected):
            if other_sel is None:
                continue

            key_pair = (min(idx, other_idx), max(idx, other_idx))
            if key_pair not in pair_keys:
                continue

            common_keys = pair_keys[key_pair]

            for key in common_keys:
                val_candidate = candidate.get(key)
                val_other = other_sel.get(key)

                # Special handling for employee ID related keys
                emp_key_group = {"emp_id", "sender_emp_id", "recipient_emp_id", "raised_by_emp_id"}

                if key in emp_key_group:
                    if not self.employee_ids_match(candidate, other_sel):
                        return False
                else:
                    # Normal equality check for other keys
                    if val_candidate != val_other:
                        return False
        return True

    def backtrack_select(self, datasets, pair_keys, selected, dataset_names, idx=0):
        # If all datasets have been selected, return the selected combination
        if idx == len(datasets):
            return selected

        candidates = datasets[idx][:]
        random.shuffle(candidates)  # Shuffle candidates to randomize selection order
        # Iterate over all candidate entries in the current dataset (idx)
        for candidate in candidates:
            # Check consistency with already selected candidates
            if self.consistent_with_selections(candidate, selected, pair_keys, idx, datasets, dataset_names[idx]):
                selected[idx] = candidate
                # Recurse to next dataset index
                result = self.backtrack_select(datasets, pair_keys, selected, dataset_names, idx + 1)
                if result is not None:
                    return result
                # Backtrack if no valid selection found at deeper levels
                selected[idx] = None

        # No consistent selection found for this dataset
        return None

    def main(self, json_files, dataset_names, task_domain):
        datasets = [self.load_json(f, dataset_names[i], task_domain) for i, f in enumerate(json_files)]
        pair_keys = self.build_pair_keys(datasets, dataset_names)
        # print("Pair keys:", pair_keys)
        selected = [None] * len(datasets)
        result = self.backtrack_select(datasets, pair_keys, selected, dataset_names)
        return result