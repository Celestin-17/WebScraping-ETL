import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime as dt
import sqlite3

def log_progress(message):
    """ Logs every process in code_log.txt """
    timestamp_format = "%Y-%h-%d-%H:%M:%S"
    now = dt.datetime.now()
    timestamp = now.strftime(timestamp_format)
    with open("./code_log.txt","a") as file:
        file.write(timestamp + " : " + message + "\n")
    return print(f"Logs ({timestamp}) : {message}")

def extract(url, table_attribs):
    """ Extracts from wikipedia the table containing the top 10 largest banks """
    log_progress("Preliminaries complete. Initiating ETL process.")
    try:
        with requests.get(url) as response:
            if response.status_code != 200: return "Connection failed !"
            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table")
            banks_table = tables[0]
            rows = banks_table.find_all("tr")
            bank_names = []
            market_cap = []
            df = pd.DataFrame(columns=table_attribs)
            for row in rows:
                cells = row.find_all("a")
                if cells:
                    bank_names.append(cells[1].get_text(strip=True))
            for row in rows:
                cells = row.find_all("td")
                if cells:
                    market_cap.append(float(cells[2].get_text(strip=True)))
            df["Name"] = bank_names
            df["MC_USD_Billion"] = market_cap
            log_progress("Data extraction complete. Initiating Transformation process.")
            return df
    except Exception as e:
        return log_progress(f"Extract(): Error encountered ({e})")

def transform(df, csv_path):
    """ Converts and adds new currencies based on exhange_rate.csv """
    csv_file = pd.read_csv(csv_path)
    eur_rate = csv_file["Rate"].iloc[0]
    gbp_rate = csv_file["Rate"].iloc[1]
    inr_rate = csv_file["Rate"].iloc[2]
    marketcap_list = df["MC_USD_Billion"].tolist()
    GBP_list = [round(x * gbp_rate, 2) for x in marketcap_list]
    EUR_list = [round(x * eur_rate, 2) for x in marketcap_list]
    INR_list = [round(x * inr_rate, 2) for x in marketcap_list]
    df.insert(1, "MC_GBP_Billion", GBP_list)
    df.insert(1, "MC_EUR_Billion", EUR_list)
    df.insert(1, "MC_INR_Billion", INR_list)
    log_progress("Transformation process complete.")
    return df

def load_phase(df, sql_connection, table_name, output_path):
    """ Loads the transformed dataframe into SQLite3 db and exports locally to .csv """
    log_progress("Initiating loading process into SQLite3 Database.")
    try:
        with sqlite3.connect(sql_connection) as conn:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            df.to_csv(output_path)
            return log_progress("Succesfully loaded into database." + "\n")
    except Exception as e:
        print(f"Exception occured: Check the logs !")
        return log_progress(f"Extract(): Error encountered ({e})")

config = {
    "URL" :"https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks",
    "table_columns" : ["Name", "MC_USD_Billion"],
    "db" : "Banks.db",
    "table" : "Largest_banks",
    "output_path" : "./Largest_banks_data.csv",
    "csv_path" : "exchange_rate.csv"
}

if __name__ == "__main__":
    df = extract(config["URL"], table_attribs=config["table_columns"])
    df = transform(df, config["csv_path"])
    load_phase(df, config["db"], config["table"], config["output_path"])



