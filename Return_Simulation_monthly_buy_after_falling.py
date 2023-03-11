import codecs
import datetime
import os
import time

import cnum
import tqdm as tqdm
from dateutil.relativedelta import relativedelta

from stock_calculation import utils

PJ_dir = "Return_Simulation/Return_Simulation_Timing/buy_after_falling/"
asset_log_dir = PJ_dir + "asset_log/"
dump_dir = PJ_dir + "dump/"
out_dir = PJ_dir + "output/"
inflation_rate = 0

monthly_income = 1000


def calculate_return_monthly_buy_after_falling_single_try(sheet_tuple, change_rate_threshold_low,
                                                          change_rate_threshold_high, startdate, invest_years,
                                                          monthly_income, inflation_rate=0):
    startdate = utils.return_calculatable_date(sheet_tuple, startdate)
    current_month = startdate
    invested_asset = 0
    invested_months = 0
    wallet = 0
    elapsed_months = 0
    sold_count = 0
    wallet_count = 0
    n1_price = sheet_tuple[utils.get_index(sheet_tuple, current_month)][1]
    while utils.canbe_simulated_monthly(sheet_tuple, current_month, 1) and elapsed_months / 12 < invest_years:
        if current_month == sheet_tuple[0][0]:  # シート一番最初の月は投資せずwalletに貯めておく
            wallet += monthly_income
            wallet_count += 1
            current_month = utils.return_calculatable_date(sheet_tuple, current_month + relativedelta(months=1))
            elapsed_months += 1
            continue
        n2_price = sheet_tuple[utils.get_index(sheet_tuple, current_month)][1]
        growth_rate = (n2_price - n1_price) / n1_price
        invested_asset = int(invested_asset * (1 + growth_rate) * (1 - inflation_rate))
        if growth_rate >= change_rate_threshold_high:
            wallet += monthly_income + invested_asset
            wallet_count += 1
            invested_asset = 0
            sold_count += 1
        elif growth_rate < change_rate_threshold_low:
            invested_asset += monthly_income + wallet
            wallet = 0
            invested_months += 1
            invested_amount = (wallet_count + invested_months) * monthly_income
        else:
            wallet += monthly_income
            wallet_count += 1

        n1_price = n2_price
        current_month = utils.return_calculatable_date(sheet_tuple,
                                                       (current_month + relativedelta(months=1)).replace(day=1))
        elapsed_months += 1
    return invested_amount, invested_asset, wallet, invested_months, sold_count, elapsed_months


def calculate_return_monthly_buy_after_falling_iterate(ticker, change_rate_threshold_low, change_rate_threshold_high,
                                                       startdate: datetime, enddate: datetime, invest_years,
                                                       monthly_income, inflation_rate=0, asset_log_dir=""):
    """
    calculate_return_monthly_buy_after_falling_single_try(sheet_tuple, change_rate_threshold_low, change_rate_threshold_high, startdate, invest_years, monthly_income, inflation_rate=0):
    iterate monthly
    """
    # initialize
    utils.make_dir(asset_log_dir)
    if asset_log_dir != "":
        asset_logfile = asset_log_dir + "{}_start_{}_invest_{}years_inflation_{:.1f}percent_changeRateLow_{}_changeRateHigh_{}.txt".format(
            ticker, startdate.strftime("%Y%m%d"), invest_years, inflation_rate * 100,
            change_rate_threshold_low, change_rate_threshold_high
        )
        if (os.path.isfile(asset_logfile)):
            os.remove(asset_logfile)

    current_date = startdate
    month_count = 0
    asset_result_list = []  # 何年から始めて資産がどのくらい残ったか
    asset_list = []
    invested_amount_list = []
    invested_months_list = []
    sold_count_list = []
    sheet_tuple = utils.get_tuple_1886_monthly(ticker)
    # end initialization

    while utils.canbe_simulated_yearly(sheet_tuple, current_date, invest_years) and (
            current_date + relativedelta(years=invest_years) < enddate):
        month_count += 1
        print("case: {}, from {} to {}, {}".format(month_count, current_date.strftime("%Y/%m/%d"),
                                                   (current_date + relativedelta(years=invest_years)).strftime(
                                                       "%Y/%m/%d"),
                                                   datetime.datetime.fromtimestamp(
                                                       time.time()).strftime("%H:%M:%S")),
              file=codecs.open(asset_logfile, "a", "utf-8"))
        invested_amount, invested_asset, wallet, invested_months, sold_count, elapsed_months = \
            calculate_return_monthly_buy_after_falling_single_try(
                sheet_tuple, change_rate_threshold_low, change_rate_threshold_high, current_date, invest_years,
                monthly_income, inflation_rate)

        asset_result_list.append(
            [current_date, invest_years, invested_amount, invested_asset, wallet, invested_months, elapsed_months])
        asset_list.append(invested_asset + wallet)
        invested_amount_list.append(invested_amount)
        invested_months_list.append(invested_months)
        sold_count_list.append(sold_count)
        if invested_amount == 0:
            print("投資できませんでした", file=codecs.open(asset_logfile, "a", "utf-8"))
        else:
            print(f"{cnum.jp(int(invested_amount))}円投資し、{invest_years}年後の資産は"
                  f"{cnum.jp(int(invested_asset + wallet))}円({((invested_asset + wallet) / invested_amount):.1f}倍)になりました。"
                  f"投資回数：{invested_months}、財布内：{cnum.jp(int(wallet))}円、sold count: {sold_count}",
                  file=codecs.open(asset_logfile, "a", "utf-8"))
        current_date = utils.return_calculatable_date(sheet_tuple,
                                                      (current_date + relativedelta(months=1)).replace(day=1))
    return asset_result_list, asset_list, invested_amount_list, invested_months_list, sold_count_list


def generate_dumpfiles_monthly_buy_after_selling(
        ticker, change_rate_threshold_low, change_rate_threshold_high, startdate: datetime, enddate, invest_years,
        monthly_income,
        inflation_rate=0, dump_dir="", out_dir="", asset_log_dir=""):
    utils.make_dir(dump_dir)
    utils.make_dir(out_dir)
    asset_result_list, asset_list, invested_amount_list, invested_months_list, sold_count_list = \
        calculate_return_monthly_buy_after_falling_iterate(
            ticker, change_rate_threshold_low, change_rate_threshold_high, startdate, enddate, invest_years,
            monthly_income, inflation_rate, asset_log_dir
        )

    if dump_dir != "":
        utils.save_to_dump(
            dump_dir,
            asset_result_list=asset_result_list,
            asset_list=asset_list,
            invested_amount_list=invested_amount_list,
            invested_months_list=invested_months_list,
            sold_count_list=sold_count_list
        )
    if out_dir != "":
        utils.save_results_to_txt(out_dir,
                                  asset_result_list=asset_result_list,
                                  asset_list=asset_list,
                                  invested_amount_list=invested_amount_list,
                                  invested_months_list=invested_months_list,
                                  sold_count_list=sold_count_list
                                  )
    return asset_result_list, asset_list, invested_amount_list, invested_months_list, sold_count_list


if __name__ == '__main__':
    starttime = time.time()
    print("start: {}".format(datetime.datetime.fromtimestamp(starttime).strftime("%H:%M:%S")))

    SPX_tuple = utils.get_tuple_1886_monthly("SPX")
    startdate = SPX_tuple[0][0]
    enddate = SPX_tuple[-1][0]
    change_rate_threshold_low_list = [i / 100 for i in range(-1, -11, -1)]
    change_rate_threshold_high_list = [i / 100 for i in range(1, 11, 1)] + [999]  # 999 means never sell
    for ticker in ["SPX", "SPXL", "SSO"]:
        for invest_years in tqdm.tqdm([30, 10, 20, 40, 50],
                                      desc=f"{ticker}, calculate invest years"):
            for change_rate_threshold_low in tqdm.tqdm(change_rate_threshold_low_list, desc=f"calculate by lows"):
                for change_rate_threshold_high in change_rate_threshold_high_list:
                    generate_dumpfiles_monthly_buy_after_selling(
                        ticker, change_rate_threshold_low, change_rate_threshold_high, startdate, enddate, invest_years,
                        monthly_income, inflation_rate,
                        dump_dir + f"{ticker}_{invest_years}years_changeRateLow_{change_rate_threshold_low}_changeRateHigh_{change_rate_threshold_high}/",
                        out_dir + f"{ticker}_{invest_years}years_changeRateLow_{change_rate_threshold_low}_changeRateHigh_{change_rate_threshold_high}/",
                        asset_log_dir)

    print("end: {}".format(datetime.datetime.fromtimestamp(time.time()).strftime("%H:%M:%S")))

    time1 = time.time()
    print("経過秒数：{}".format(int(time1 - starttime)))
