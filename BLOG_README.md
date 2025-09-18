# EnterpriseBench Research Blog

This directory contains the GitHub Pages blog for the EnterpriseBench research project.

## Structure

- `index.md` - Main blog content with comprehensive project overview
- `_config.yml` - Jekyll configuration
- `_layouts/` - HTML templates for the blog
- `assets/` - CSS styles and images
- `Gemfile` - Ruby dependencies for Jekyll
- `.github/workflows/` - GitHub Actions for automatic deployment

## Local Development

To run the blog locally:

1. Install Ruby and Bundler
2. Run `bundle install` to install dependencies
3. Run `bundle exec jekyll serve` to start the development server
4. Visit `http://localhost:4000` to view the site

## Deployment

The blog is automatically deployed to GitHub Pages when changes are pushed to the main branch using GitHub Actions.

## Content Sections

The blog includes:

- **Abstract**: Project overview and key contributions
- **Introduction**: Problem statement and motivation
- **Framework**: Technical architecture and components
- **Domains**: Supported enterprise domains and features
- **Evaluation**: Methods and performance metrics
- **Demos**: Interactive Streamlit applications
- **Implementation**: Setup and usage instructions
- **Authors**: Research team information
- **Citation**: BibTeX citation format

## Visual Elements

The blog includes several custom visualizations:

- Architecture diagram showing system components
- Evaluation process flowchart
- Domain coverage bubble chart
- Performance analysis charts

All images are generated programmatically and stored in `assets/images/`.

## Styling

The blog uses a custom CSS theme inspired by modern academic websites with:

- Clean, professional design
- Responsive layout for mobile devices
- Interactive elements and hover effects
- Consistent color scheme and typography
- Accessible design principles