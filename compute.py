from os import path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import requests
from datetime import datetime, timedelta
import logging

DAYS_LAST_YEAR = 260
DAYS_LAST_MONTH = 21

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)-8s - %(message)s', datefmt='%y-%m-%d %H:%M:%S')

log = logging.getLogger(__name__)

def fetch_last_date(file_path) -> datetime:
    df = pd.read_excel(file_path)
    return df.loc[:,'Date'].max().to_pydatetime()


def get_ohlc_data(base_url: str, from_date: datetime, file_path: str) -> str:
    # https://archives.nseindia.com/content/indices/ind_close_all_14072023.csv
    current_date = from_date + timedelta(days=1)
    today = datetime.now()
    df_all = pd.DataFrame()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-IN,en;q=0.9',
        'Referer': 'https://www.nseindia.com/all-reports',
        'DNT': '1',
        'Connection': 'keep-alive',
    }

    while current_date < today:
        date_str = current_date.strftime('%d%m%Y')
        csv_path = path.join(path.dirname(file_path), f"{date_str}.csv")
        if current_date.weekday() not in [5, 6]:
            try:
                resp = requests.get(f"{base_url}{date_str}.csv", headers=headers)
                with open(csv_path, "w") as f:
                    f.write(resp.content.decode("utf-8"))
            except Exception as e:
                log.exception(f"Error occurred while fetching data for {current_date}")
                current_date = current_date + timedelta(days=1)
                continue

            if resp.status_code == 200:
                log.info(f"http get success for {current_date}")

                current_date = current_date + timedelta(days=1)
                df = pd.read_csv(csv_path)
                df_all = pd.concat([df_all, df.loc[df['Index Name']=="Nifty 50", ['Index Date',
                                                      'Open Index Value',
                                                      'High Index Value',
                                                      'Low Index Value',
                                                      'Closing Index Value']]],
                                    ignore_index= True)
            else:
                log.warning(f"Status code not 200 date={current_date}, status_code={resp.status_code} content={resp.content}")
                current_date = current_date + timedelta(days=1)
                continue
        else:
            log.info(f"Skipping as weekday is {current_date.weekday()}")
            current_date = current_date + timedelta(days=1)

    if len(df_all) > 0:
        log.info(f"{len(df_all)} records found")
        df_all.rename(columns={"Index Date": "Date",
                               "Open Index Value": "Open",
                               "High Index Value": "High",
                               "Low Index Value": "Low",
                               "Closing Index Value": "Close"}, inplace=True)
        df_all['Date']=pd.to_datetime(df_all['Date'], format="%d-%m-%Y")

        df_existing = pd.read_excel(file_path)
        df_existing = pd.concat([df_existing, df_all], ignore_index=True)

        output_path = path.join(path.dirname(file_path), path.basename(file_path))
        with pd.ExcelWriter(output_path,
                            engine='xlsxwriter',
                            date_format='dd-mm-yyyy') as writer:
            df_existing.to_excel(writer, index=False)
        return output_path
    else:
        return ""


def get_fit_for_degree(degree,X,y):
    poly_reg = PolynomialFeatures(degree=degree)
    X_poly = poly_reg.fit_transform(X)
    lin_reg = LinearRegression()
    lin_reg.fit(X_poly, y)
    return lin_reg, poly_reg


def generate_plots(file_path:str, data_last_date: str):
    df = pd.read_excel(file_path)
    # df['Date']=pd.to_datetime(df['Date'], format="%d %b %Y")
    df.sort_values(by='Date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(0,"Serial",range(0,len(df)))

    X = df.iloc[:,0:1]
    y = df.loc[:, "Close"]

    # lin_reg = LinearRegression()
    # lin_reg.fit(X, y)
    # sns.lineplot(x=X.iloc[:,0],y=lin_reg.predict(X))
    # sns.lineplot(x=X.iloc[:,0],y=y)
    # plt.show()

    # poly_reg = PolynomialFeatures(degree = 2)
    # X_poly = poly_reg.fit_transform(X)
    # # poly_reg.fit(X_poly, y)
    # lin_reg_2 = LinearRegression()
    # lin_reg_2.fit(X_poly, y)
    # sns.lineplot(x=df.iloc[:,1],y=y)
    # sns.lineplot(x=df.iloc[:,1],y=lin_reg_2.predict(poly_reg.fit_transform(X)))
    # plt.show()

    lin_deg1, poly_deg1 = get_fit_for_degree(1, X, y)
    lin_deg2, poly_deg2 = get_fit_for_degree(2, X, y)
    lin_deg3, poly_deg3 = get_fit_for_degree(3, X, y)
    lin_deg4, poly_deg4 = get_fit_for_degree(4, X, y)
    df['degree1'] = lin_deg1.predict(poly_deg1.fit_transform(X))
    df['degree2'] = lin_deg2.predict(poly_deg2.fit_transform(X))
    df['degree3'] = lin_deg3.predict(poly_deg3.fit_transform(X))
    df['degree4'] = lin_deg4.predict(poly_deg4.fit_transform(X))
    df['avg'] = df[['degree2','degree3','degree4']].mean(axis=1)

    plt.figure(figsize=(11,6.5))
    sns.lineplot(data=df, x='Date', y='Close')
    sns.lineplot(data=df, x='Date', y='avg').set(title=f"Updated: {datetime.now().strftime('%Y-%m-%d')}   Data upto: {data_last_date}")
    # sns.lineplot(x=df.iloc[:,1],y=df['avg'])
    plt.savefig(path.join(path.dirname(file_path), "plot.jpg"),bbox_inches='tight')
    # plt.show()
    plt.close()

    LAST_YEAR_INDEX = len(df) - DAYS_LAST_YEAR
    plt.figure(figsize=(11,6.5))
    sns.lineplot(data=df[LAST_YEAR_INDEX:], x='Date', y='Close')
    sns.lineplot(data=df[LAST_YEAR_INDEX:], x='Date', y='avg').set(title=f"Updated: {datetime.now().strftime('%Y-%m-%d')}   Data upto: {data_last_date}")
    plt.savefig(path.join(path.dirname(file_path), "plot_last_year.jpg"), bbox_inches='tight')
    # plt.show()
    plt.close()


def nifty50_trend(base_path):
    data_file = "NIFTY 50_Data.xlsx"
    base_url = "https://archives.nseindia.com/content/indices/ind_close_all_"
    file_path = path.join(base_path, data_file)
    last_date = fetch_last_date(file_path)

    log.info(f"Last update date in excel: {last_date}")
    output_file = get_ohlc_data(base_url=base_url, from_date=last_date, file_path=file_path)

    if output_file:
        log.info(f"New data stored in {output_file}")
        data_last_date = fetch_last_date(output_file).strftime("%Y-%m-%d")
        generate_plots(file_path=output_file, data_last_date=data_last_date)
    else:
        log.info("No new data found")


def main():
    log.info("Starting")
    nifty50_trend(base_path="data/nifty50/")
    log.info("Finished")


if __name__ == "__main__":
    main()