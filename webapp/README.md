# CellVerse Web Application

## Session Management

### Clearing Added Diseases
When you upload PDFs, the application adds new diseases to your session. There are two ways to clear these added diseases:

1. **Using the Reset Button**: On the home page, if you've added any diseases, a "Reset Discovered Diseases" button appears below the disease selection area. Click this button to remove all discovered diseases.

2. **Manually Clearing Session Data**: If the reset button doesn't work or you prefer a manual approach:
   - In your browser, open Developer Tools (F12 or Ctrl+Shift+I)
   - Go to the Application tab
   - Under Storage, select Cookies, then find the session cookie for your site
   - Delete this cookie to clear your session
   - Refresh the page

3. **Restarting the Application**: A full restart of the Flask application will clear all session data as long as `session.permanent` is not set to True.

### PDF Naming Convention
For demonstration purposes, the application recognizes specific PDF filenames:

- `chronic_lymphotic_leukemia.pdf` - Adds Chronic Lymphocytic Leukemia and its treatments
- `non_hodgkin_lymphoma.pdf` - Adds Non-Hodgkin Lymphoma and its treatments
- `acute_myeloid_leukemia.pdf` - Adds Acute Myeloid Leukemia and its treatments

Other PDF names will still be processed but may default to a predetermined disease.
