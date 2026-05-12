# LIMS Function Search Web App

This is a simple static web app that lets you search LIMS Basic function definitions and view their parsed content.

## Deployment

1. Deploy the `app/` folder as a static site on Netlify.
2. Ensure `functions.json`, `index.html`, `script.js`, and `style.css` are published.

## Usage

- Open the app in the browser.
- Search by function name or keyword.
- The app shows the matching function definition.

## Data Source

The app uses `functions.json` as its local search database.

## Regenerating data

To regenerate `functions.json` from the source text file, run the generator script:

```bash
python3 app/generate_functions_json.py
```
