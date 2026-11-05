import os
import re
import time
import traceback
import csv
import pandas as pd
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup
from DrissionPage import ChromiumPage, ChromiumOptions

# --- KONFIGURACJA ---
FILE_NEW = 'ranking_skrzynek.csv'
FILE_BACKUP = 'ranking_skrzynek_backup.csv'
THRESHOLD = -0.5

# --- 1. MODUŁ ALERTÓW MACOS ---
def trigger_mac_alert(message):
    applescript = f'display notification "{message}" with title "Monitor RTP" subtitle "⚠️ Wykryto spadek opłacalności" sound name "Basso"'
    try:
        subprocess.run(['osascript', '-e', applescript])
    except Exception as e:
        print(f"Błąd powiadomienia macOS: {e}")

def check_rtp_drops():
    if not os.path.exists(FILE_BACKUP) or not os.path.exists(FILE_NEW):
        print("Brak kompletu plików do porównania delty (to prawdopodobnie pierwsze uruchomienie).")
        return

    df_old = pd.read_csv(FILE_BACKUP, delimiter=';')
    df_new = pd.read_csv(FILE_NEW, delimiter=';')
    
    df_old['Zwrot RTP (%)'] = df_old['Zwrot RTP (%)'].astype(str).str.replace(',', '.').astype(float)
    df_new['Zwrot RTP (%)'] = df_new['Zwrot RTP (%)'].astype(str).str.replace(',', '.').astype(float)
    
    merged = pd.merge(df_new, df_old, on='Skrzynka', suffixes=('_nowe', '_stare'))
    merged['RTP_Delta'] = merged['Zwrot RTP (%)_nowe'] - merged['Zwrot RTP (%)_stare']
    
    drops = merged[merged['RTP_Delta'] <= THRESHOLD]
    
    if not drops.empty:
        alert_msg = f"Spadki ({datetime.now().strftime('%H:%M')}):\n"
        for _, row in drops.iterrows():
            alert_msg += f"{row['Skrzynka']}: {row['RTP_Delta']:.2f}%\n"
        trigger_mac_alert(alert_msg)
        print(f"⚠️ [ALARM]\n{alert_msg}")
    else:
        print("Parametry stabilne. Brak anomalii.")

# --- 2. MODUŁ SCRAPOWANIA ---
def setup_browser():
    print("Inicjalizacja przeglądarki...")
    co = ChromiumOptions()
    co.auto_port()
    co.set_browser_path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    return ChromiumPage(co)

def scrape_case_with_browser(page, url, case_name):
    try:
        print(f"\n--- SKANOWANIE: {case_name} ---")
        page.set.timeouts(page_load=15)
        
        try:
            page.get(url)
        except:
            pass
        
        case_price = None
        for _ in range(15):
            html_content = page.html
            price_match = re.search(r'"price"\s*:\s*([\d.]+)\s*,\s*"priceCurrency"', html_content)
            if price_match:
                case_price = float(price_match.group(1))
                break
            time.sleep(1)
            
        if case_price is not None:
            print(f"✅ Cena: {case_price} PLN")
        else:
            print("❌ Nie znaleziono ceny (Cloudflare / błąd ładowania).")
            return None
            
        if not page.wait.ele_displayed('.ContainerGroupedItem_name', timeout=15):
            print("❌ Skrypt poddał się - skiny nie pojawiły się w ciągu 15 sekund.")
            return None
            
        final_html = page.html
        soup = BeautifulSoup(final_html, 'html.parser')
        items_data = []
        
        names = soup.find_all(class_='ContainerGroupedItem_name')
        tables = soup.find_all(class_='ContainerGroupedItem_chances')
        
        if not names or not tables:
            print("❌ Błąd: Nie odnaleziono nazw i tabel.")
            return None
            
        for name_ele, chances_div in zip(names, tables):
            base_name = name_ele.get_text(strip=True)
            rows = chances_div.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    condition = cells[0].get_text(strip=True)
                    price_text = cells[1].get_text(strip=True).replace(',', '.')
                    odds_text = cells[3].get_text(strip=True).replace(',', '.')
                    
                    full_name = f"{base_name} ({condition})"
                    value_str = ''.join(c for c in price_text if c.isdigit() or c == '.')
                    prob_str = ''.join(c for c in odds_text if c.isdigit() or c == '.')
                    
                    if value_str and prob_str:
                        try:
                            items_data.append({
                                "name": full_name,
                                "value": float(value_str),
                                "prob": float(prob_str)
                            })
                        except ValueError:
                            pass
        
        print(f"✅ Pobrano {len(items_data)} wariantów.")
        return {"name": case_name, "price": case_price, "items": items_data}
        
    except Exception as e:
        print("❌ BŁĄD PODCZAS PRACY SKRYPTU:")
        traceback.print_exc()
        return None

def analyze_case(case_data):
    if not case_data or not case_data['items']:
        return None
        
    case_name = case_data['name']
    case_price = case_data['price']
    items = case_data['items']
    
    expected_value = sum(item['value'] * (item['prob'] / 100.0) for item in items)
    rtp = (expected_value / case_price) * 100
    profit_prob = sum(item['prob'] for item in items if item['value'] > case_price)

    return {
        "name": case_name,
        "price": case_price,
        "ev": expected_value,
        "rtp": rtp,
        "profit_prob": profit_prob
    }

def pl_format(value, decimals=2):
    return f"{value:.{decimals}f}".replace('.', ',')

def run_scraper():
    cases_to_check = [
        {"name": "Low Case", "url": "https://csgo-skins.com/case/low-case"},
        {"name": "Low Case Boosted", "url": "https://csgo-skins.com/case/low-case-boosted"},
        {"name": "Indirect Case", "url": "https://csgo-skins.com/case/indirect-case"},
        {"name": "Indirect Case Boosted", "url": "https://csgo-skins.com/case/indirect-case-boosted"},
        {"name": "Medium Case", "url": "https://csgo-skins.com/case/medium-case"},
        {"name": "Medium Case Boosted", "url": "https://csgo-skins.com/case/medium-case-boosted"},
        {"name": "Ultra Case", "url": "https://csgo-skins.com/case/ultra-case"},
        {"name": "Ultra Case Boosted", "url": "https://csgo-skins.com/case/ultra-case-boosted"},
        {"name": "Ammo Case", "url": "https://csgo-skins.com/case/ammo-case"},
        {"name": "Ammo Case Boosted", "url": "https://csgo-skins.com/case/ammo-case-boosted"},
        {"name": "Rust Case", "url": "https://csgo-skins.com/case/rust-case"},
        {"name": "Rust Case Boosted", "url": "https://csgo-skins.com/case/rust-case-boosted"},
        {"name": "Cargo Case", "url": "https://csgo-skins.com/case/cargo-case"},
        {"name": "Cargo Case Boosted", "url": "https://csgo-skins.com/case/cargo-case-boosted"},
        {"name": "C4 Case", "url": "https://csgo-skins.com/case/c4-case"},
        {"name": "C4 Case Boosted", "url": "https://csgo-skins.com/case/c4-case-boosted"},
        {"name": "Ruined Case", "url": "https://csgo-skins.com/case/ruined-case"},
        {"name": "Ruined Case Boosted", "url": "https://csgo-skins.com/case/ruined-case-boosted"},
        {"name": "Ember Case", "url": "https://csgo-skins.com/case/ember-case"},
        {"name": "Ember Case Boosted", "url": "https://csgo-skins.com/case/ember-case-boosted"},
        {"name": "Military Case", "url": "https://csgo-skins.com/case/military-case"},
        {"name": "Military Case Boosted", "url": "https://csgo-skins.com/case/military-case-boosted"},
        {"name": "Bamboo Case", "url": "https://csgo-skins.com/case/bamboo-case"},
        {"name": "Bamboo Case Boosted", "url": "https://csgo-skins.com/case/bamboo-case-boosted"},
        {"name": "Chocolate Case", "url": "https://csgo-skins.com/case/chocolate-case"},
        {"name": "Chocolate Case Boosted", "url": "https://csgo-skins.com/case/chocolate-case-boosted"},
        {"name": "Sandstorm Case", "url": "https://csgo-skins.com/case/sandstorm-case"},
        {"name": "Sandstorm Case Boosted", "url": "https://csgo-skins.com/case/sandstorm-case-boosted"},
        {"name": "Neon Case", "url": "https://csgo-skins.com/case/neon-case"},
        {"name": "Neon Case Boosted", "url": "https://csgo-skins.com/case/neon-case-boosted"},
        {"name": "Plague Case", "url": "https://csgo-skins.com/case/plague-case"},
        {"name": "Plague Case Boosted", "url": "https://csgo-skins.com/case/plague-case-boosted"},
        {"name": "Toolbox Case", "url": "https://csgo-skins.com/case/toolbox-case"},
        {"name": "Toolbox Case Boosted", "url": "https://csgo-skins.com/case/toolbox-case-boosted"},
        {"name": "Wasteland Case", "url": "https://csgo-skins.com/case/wasteland-case"},
        {"name": "Wasteland Case Boosted", "url": "https://csgo-skins.com/case/wasteland-case-boosted"},
        {"name": "Anubis Case", "url": "https://csgo-skins.com/case/anubis-case"},
        {"name": "Anubis Case Boosted", "url": "https://csgo-skins.com/case/anubis-case-boosted"},
        {"name": "Lovely Case", "url": "https://csgo-skins.com/case/lovely-case"},
        {"name": "Lovely Case Boosted", "url": "https://csgo-skins.com/case/lovely-case-boosted"},
        {"name": "Steampunk Case", "url": "https://csgo-skins.com/case/steampunk-case"},
        {"name": "Steampunk Case Boosted", "url": "https://csgo-skins.com/case/steampunk-case-boosted"},
        {"name": "Prickly Case", "url": "https://csgo-skins.com/case/prickly-case"},
        {"name": "Prickly Case Boosted", "url": "https://csgo-skins.com/case/prickly-case-boosted"},
        {"name": "Autumn Case", "url": "https://csgo-skins.com/case/autumn-case"},
        {"name": "Autumn Case Boosted", "url": "https://csgo-skins.com/case/autumn-case-boosted"},
        {"name": "GigaBuła Case", "url": "https://csgo-skins.com/case/gigabula-case"},
        {"name": "GigaBuła Case Boosted", "url": "https://csgo-skins.com/case/gigabula-case-boosted"},
        {"name": "Slime Case", "url": "https://csgo-skins.com/case/slime-case"},
        {"name": "Slime Case Boosted", "url": "https://csgo-skins.com/case/slime-case-boosted"},
        {"name": "Striking Ninja Case", "url": "https://csgo-skins.com/case/striking-n-case"},
        {"name": "Striking Ninja Case Boosted", "url": "https://csgo-skins.com/case/striking-n-case-boosted"},
        {"name": "Ninja Case", "url": "https://csgo-skins.com/case/ninja-case"},
        {"name": "Ninja Case Boosted", "url": "https://csgo-skins.com/case/ninja-case-boosted"},
        {"name": "Duck Case", "url": "https://csgo-skins.com/case/duck-case"},
        {"name": "Duck Case Boosted", "url": "https://csgo-skins.com/case/duck-case-boosted"},
        {"name": "Cursed Case", "url": "https://csgo-skins.com/case/cursed-case"},
        {"name": "Cursed Case Boosted", "url": "https://csgo-skins.com/case/cursed-case-boosted"},
        {"name": "Honey Case", "url": "https://csgo-skins.com/case/honey-case-v1"},
        {"name": "Honey Case Boosted", "url": "https://csgo-skins.com/case/honey-case-v1-boosted"},
        {"name": "Predator Case", "url": "https://csgo-skins.com/case/predator-case"},
        {"name": "Predator Case Boosted", "url": "https://csgo-skins.com/case/predator-case-boosted"},
        {"name": "Tribal Case", "url": "https://csgo-skins.com/case/tribal-case"},
        {"name": "Tribal Case Boosted", "url": "https://csgo-skins.com/case/tribal-case-boosted"},
        {"name": "Ruthless Case", "url": "https://csgo-skins.com/case/ruthless-case"},
        {"name": "Ruthless Case Boosted", "url": "https://csgo-skins.com/case/ruthless-case-boosted"},
        {"name": "Saloon Case", "url": "https://csgo-skins.com/case/saloon-case"},
        {"name": "Saloon Case Boosted", "url": "https://csgo-skins.com/case/saloon-case-boosted"},
        {"name": "Water Case", "url": "https://csgo-skins.com/case/water-case"},
        {"name": "Water Case Boosted", "url": "https://csgo-skins.com/case/water-case-boosted"},
    ]
    
    all_rankings = []
    all_skins = []
    browser_page = setup_browser()
    
    try:
        for case_info in cases_to_check:
            data = scrape_case_with_browser(browser_page, case_info["url"], case_info["name"])
            
            if data:
                stats = analyze_case(data)
                if stats:
                    all_rankings.append(stats)
                
                for item in data['items']:
                    all_skins.append({
                        "case_name": case_info["name"],
                        "skin_name": item["name"],
                        "value": item["value"],
                        "prob": item["prob"]
                    })
            time.sleep(3)
    finally:
        if browser_page:
            browser_page.quit()

    if not all_rankings:
        print("\n❌ Krytyczny błąd: Żadna skrzynka nie została pobrana poprawnie.")
    else:
        all_rankings.sort(key=lambda x: x["rtp"], reverse=True)
        print("\n--- TWORZENIE PLIKÓW CSV ---")
    
    with open(FILE_NEW, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['Skrzynka', 'Koszt otwarcia (PLN)', 'Wartość oczekiwana EV (PLN)', 'Zwrot RTP (%)', 'Szansa na zysk (%)'])
        for r in all_rankings:
            writer.writerow([r['name'], pl_format(r['price'], 2), pl_format(r['ev'], 2), pl_format(r['rtp'], 2), pl_format(r['profit_prob'], 3)])
            
    with open('wszystkie_skiny.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['Skrzynka', 'Skin', 'Wartość (PLN)', 'Szansa (%)'])
        for skin in all_skins:
            writer.writerow([skin['case_name'], skin['skin_name'], pl_format(skin['value'], 2), pl_format(skin['prob'], 3)])

    print(f"✅ Gotowe! Pomyślnie zrzucono {len(all_rankings)} skrzynek do CSV.")

# --- 3. GŁÓWNA LOGIKA WYKONAWCZA (ETL) ---
def main():
    # KROK A: Zabezpieczenie poprzedniego zrzutu jako bazy porównawczej
    if os.path.exists(FILE_NEW):
        print(f"Tworzenie kopii zapasowej: {FILE_NEW} -> {FILE_BACKUP}")
        os.replace(FILE_NEW, FILE_BACKUP)
        
    # KROK B: Scrapowanie i generowanie nowych danych
    run_scraper()
    
    # KROK C: Analiza delty i powiadomienia macOS
    if os.path.exists(FILE_NEW):
        print("\n--- WERYFIKACJA SPADKÓW RTP ---")
        check_rtp_drops()

if __name__ == "__main__":
    main()
