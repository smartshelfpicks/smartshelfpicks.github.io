# Smart Shelf Picks website

Live site: https://smartshelfpicks.github.io

The pages are built automatically from the product Google Sheet ("Affilate Entry flow").
Only rows with **Show on site = Yes** appear.

- `build.py` reads the Sheet's product feed and writes the pages.
- `data/site_copy.json` holds the category guides, FAQs and About text.
- `static/assets/` holds the style sheet, logo and the small scripts for search and the contact form.
- `.github/workflows/build.yml` rebuilds and publishes the site every 3 hours, on every change here, and when you press **Run workflow** under Actions.

To refresh the site right away after editing the Sheet: Actions → Build and publish site → Run workflow.
