# Skin Case RTP & Odds Analyzer 📊

A robust, automated data pipeline and analysis tool designed to calculate the Expected Value (EV), Return to Player (RTP), and profit probabilities for dynamic skin case opening websites.

By leveraging web scraping and statistical modeling, this tool filters out mathematically suboptimal choices (like "Boosted" cases) and identifies the best strategies for mitigating variance (e.g., 4-player Shared Battles).

## 🚀 Features

*   **Dynamic Web Scraping:** Bypasses JavaScript-rendered Single Page Applications (React/Vue) using headless browser automation to extract hidden drop rates and item values.
*   **Automated ETL Pipeline:** Cleanses and transforms raw web text (prices, percentages) using RegEx and Pandas, outputting structured `.csv` datasets.
*   **Probability & RTP Engine:** Calculates the exact mathematical edge of the house and the probability of landing a profitable drop ("Profit Chance > 30%").
*   **Strategy Optimizer:** Models risk vs. reward for different modes (e.g., 1v1 vs. 4-player shared pools) to minimize variance.

## 🧮 Mathematical Modeling

The core engine evaluates each case based on Expected Value (EV) and Return to Player (RTP). The Expected Value is calculated using the standard mathematical formula:

$$EV = \sum_{i=1}^{n} (P_i \cdot V_i)$$

Where:
*   $P_i$ is the probability of dropping item $i$.
*   $V_i$ is the monetary value of item $i$.

The RTP is then derived as:

$$RTP = \left( \frac{EV}{C} \right) \cdot 100$$

*(Where $C$ is the cost of opening the case).*

## 🛠️ Tech Stack

*   **Core Logic:** Python 3
*   **Data Extraction:** Selenium, Playwright (for dynamic DOM rendering)
*   **Data Processing:** Pandas, `re` (Regular Expressions), `math`
*   **Storage:** Local CSV databases
*   **Infrastructure:** Designed to run locally on macOS/Terminal or as background cron jobs on a Raspberry Pi 4 (ext4 filesystem).

## ⚙️ Installation & Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/skin-case-analyzer.git
    cd skin-case-analyzer
    ```

2.  **Install dependencies:**
    ```bash
    pip install pandas selenium
    ```
    *(Note: Ensure you have the appropriate WebDriver installed for Selenium, e.g., ChromeDriver or GeckoDriver).*

3.  **Run the Scraper:**
    Execute the scraping script to fetch live data and update your local database.
    ```bash
    python src/scraper.py
    ```

4.  **Analyze the Data:**
    Run the analysis module to generate the top-performing cases sorted by RTP or Profit Probability.
    ```bash
    python src/analyzer.py --sort rtp
    ```

## ⚠️ Disclaimer

**This project is for educational and statistical analysis purposes only.** 
The algorithms used by case opening websites inherently favor the house (RTP < $100\%$). This tool does not guarantee profits, nor does it encourage gambling. Always manage your budget responsibly.