# InstacartFlation

A Python script that scrapes your Instacart order history and saves the data in a JSON file.

The data scraped includes:
- Order date
- Number of unique items
- Order total
- Whether the order was cancelled
- The delivery photo URL (if any)
- The list of items, where the data for each item includes:
  - Item name
  - Item unit price
  - Item unit description (usually weight if applicable)
  - Item unit quantity

## Usage

1. Ensure Python dependencies are installed: `pip install -r requirements.txt`
2. Ensure you have Chromium or Google Chrome installed.
3. Ensure you have Chrome Webdriver installed and that it is compatible with the version of Chromium/Chrome you have.
   - On Linux, you can run `installChromeDriver.sh` to automatically install/update ChromeDriver in `/usr/local/bin`,
4. Optionally, create a [`.env`](https://www.dotenv.org/docs/security/env.html) file with your Instacart credentials defined as `INSTACART_EMAIL` and `INSTACART_PASSWORD` (or ensure those environment variables are present in some other way).
   - If you skip this, you will need to login manually when the script starts.
   - Note that even with these variables defined, you may still need to manually solve the occasional [CAPTCHA](https://en.wikipedia.org/wiki/CAPTCHA).
5. Run the script: `python main.py`
   - The output is printed to the terminal; if you would like to also save it to a file, use the `--output` argument with a valid file path.
