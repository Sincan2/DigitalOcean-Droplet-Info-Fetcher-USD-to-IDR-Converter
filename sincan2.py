import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import time

# DigitalOcean API Token
API_TOKEN = "token Digitalocean"
RETRY_LIMIT = 3
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
}

# List untuk menyimpan data droplet
droplet_data_list = []

# Set up WebDriver (for example, using Chrome)
driver = webdriver.Chrome(executable_path='/path/to/chromedriver')

# Fungsi untuk mengambil kurs USD ke IDR dari situs Bank Indonesia
def fetch_usd_to_idr():
    url = "https://www.bi.go.id/id/statistik/informasi-kurs/transaksi-bi/default.aspx"
    driver.get(url)
    time.sleep(5)  # Beri waktu untuk halaman memuat sepenuhnya
    
    # Ambil elemen tabel yang berisi kurs USD
    table = driver.find_element(By.CLASS_NAME, "table1")
    rows = table.find_elements(By.TAG_NAME, "tr")
    
    # Cari kurs USD
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) > 0 and "USD" in cols[0].text:
            kurs_jual = float(cols[1].text.replace(',', ''))
            kurs_beli = float(cols[2].text.replace(',', ''))
            kurs_tengah = (kurs_jual + kurs_beli) / 2
            print(f"Kurs USD/IDR Jual: {kurs_jual}, Beli: {kurs_beli}, Tengah: {kurs_tengah}")
            return kurs_tengah

# Fungsi untuk mengambil ID dari semua droplet dengan pagination
def fetch_droplet_ids():
    print("Fetching droplet IDs...")
    droplet_ids = []
    page = 1
    per_page = 20  # Atur sesuai kebutuhan atau sesuai batas API

    while True:
        url = f"https://api.digitalocean.com/v2/droplets?page={page}&per_page={per_page}"
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code == 200:
            droplets = response.json().get('droplets', [])
            droplet_ids.extend([droplet['id'] for droplet in droplets])
            if len(droplets) < per_page:
                # Jika jumlah droplet yang ditarik kurang dari per_page, itu adalah halaman terakhir
                break
            else:
                page += 1  # Pindah ke halaman berikutnya
        else:
            print(f"Failed to fetch droplet IDs: {response.status_code}")
            break

    print(f"Total droplets found: {len(droplet_ids)}")
    return droplet_ids

# Fungsi untuk mengambil informasi droplet
def get_droplet_info(droplet_id, usd_to_idr):
    url = f"https://api.digitalocean.com/v2/droplets/{droplet_id}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        droplet = response.json().get('droplet', {})
        hostname = droplet.get('name', 'N/A')
        size_info = droplet.get('size', {})
        price = size_info.get('price_monthly', 'N/A')
        memory = size_info.get('memory', 'N/A')
        vcpus = size_info.get('vcpus', 'N/A')
        disk = size_info.get('disk', 'N/A')
        # Tambahkan konversi ke Rupiah
        price_idr = price * usd_to_idr if price != 'N/A' else 'N/A'
        return {
            'Hostname': hostname,
            'Price ($)': price,
            'Price (IDR)': price_idr,
            'Memory (MB)': memory,
            'vCPUs': vcpus,
            'Disk (GB)': disk
        }
    else:
        print(f"Error fetching droplet info (ID: {droplet_id}): {response.status_code}")
        return None

# Fungsi untuk memproses setiap droplet dan mengulang percobaan jika gagal
def process_droplet(droplet_id, usd_to_idr):
    attempt = 1
    while attempt <= RETRY_LIMIT:
        print(f"Fetching data for droplet ID {droplet_id} (Attempt {attempt})...")
        droplet_info = get_droplet_info(droplet_id, usd_to_idr)
        if droplet_info:
            # Tambahkan data droplet ke dalam list
            droplet_data_list.append(droplet_info)
            print(f"Hostname: {droplet_info['Hostname']}")
            print(f"Price ($): {droplet_info['Price ($)']}")
            print(f"Price (IDR): {droplet_info['Price (IDR)']}")
            print(f"Memory (MB): {droplet_info['Memory (MB)']}")
            print(f"vCPUs: {droplet_info['vCPUs']}")
            print(f"Disk (GB): {droplet_info['Disk (GB)']}")
            return True
        else:
            print(f"Failed to fetch data for droplet ID {droplet_id}. Retrying...")
            attempt += 1
            time.sleep(10)  # Tunggu 10 detik sebelum mencoba lagi
    
    print(f"Exceeded retry limit for droplet ID {droplet_id}.")
    return False

# Fungsi untuk menyimpan data droplet ke dalam file Excel
def save_to_excel(data_list, filename="droplet_info.xlsx"):
    df = pd.DataFrame(data_list)
    df.to_excel(filename, index=False)
    print(f"Data successfully saved to {filename}")

# Fungsi utama
def main():
    print("Starting droplet data fetching process...")
    
    usd_to_idr = fetch_usd_to_idr()
    if usd_to_idr is None:
        print("Failed to fetch USD to IDR rate. Exiting.")
        return
    
    droplet_ids = fetch_droplet_ids()
    
    success_count = 0
    failure_count = 0
    
    for droplet_id in droplet_ids:
        if process_droplet(droplet_id, usd_to_idr):
            success_count += 1
        else:
            failure_count += 1
        print("Waiting for 10 seconds before processing the next droplet...")
        time.sleep(10)
    
    print(f"Process completed. Total droplets processed successfully: {success_count}, failed: {failure_count}")
    
    if droplet_data_list:
        save_to_excel(droplet_data_list)
    else:
        print("No data to save to Excel.")
    
    driver.quit()  # Menutup browser setelah selesai

if __name__ == "__main__":
    main()

