import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime

# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 根据系统可用字体调整，如使用Mac可改为['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class CAPMAnalysisApp:
    def __init__(self, root):
        self.current_beta = None
        self.root = root
        self.root.title("202230115138唐鹏文")
        self.fund_data = None
        self.market_data = None
        self.create_widgets()

    # 主窗口
    def create_widgets(self):
        # 文件加载
        self.load_btn = ttk.Button(self.root, text="加载Excel文件", command=self.load_file)
        self.load_btn.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

        # 基金代码选择
        ttk.Label(self.root, text="选择基金代码:").grid(row=1, column=0, sticky='w')
        self.fund_code = ttk.Combobox(self.root, state='readonly')
        self.fund_code.grid(row=1, column=1, padx=10, pady=5)

        # 日期范围选择
        ttk.Label(self.root, text="开始日期:").grid(row=2, column=0, sticky='w')
        self.start_date = ttk.Combobox(self.root, state='readonly')
        self.start_date.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="结束日期:").grid(row=3, column=0, sticky='w')
        self.end_date = ttk.Combobox(self.root, state='readonly')
        self.end_date.grid(row=3, column=1, padx=10, pady=5)

        # 分析按钮组
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        self.analyze_btn = ttk.Button(button_frame, text="CAPM分析", command=self.analyze)
        self.analyze_btn.pack(side=tk.LEFT, padx=5)

        self.fund_chart_btn = ttk.Button(button_frame, text="基金收益率走势", command=self.show_fund_chart)
        self.fund_chart_btn.pack(side=tk.LEFT, padx=5)

        self.hs300_chart_btn = ttk.Button(button_frame, text="HS300走势", command=self.show_hs300_chart)
        self.hs300_chart_btn.pack(side=tk.LEFT, padx=5)

        # 主图表区域
        self.figure = plt.Figure(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().grid(row=5, column=0, columnspan=2, padx=10, pady=10)

        # 结果标签
        self.result_label = ttk.Label(self.root, text="结果将显示在这里")
        self.result_label.grid(row=6, column=0, columnspan=2, pady=10)

        # 新增输入框和输出框
        ttk.Label(self.root, text="组合价值 (V):").grid(row=7, column=0, sticky='w')
        self.portfolio_value = ttk.Entry(self.root)
        self.portfolio_value.grid(row=7, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="期货价格 (F):").grid(row=8, column=0, sticky='w')
        self.futures_price = ttk.Entry(self.root)
        self.futures_price.grid(row=8, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="合约乘数 (m):").grid(row=9, column=0, sticky='w')
        self.contract_multiplier = ttk.Entry(self.root)
        self.contract_multiplier.grid(row=9, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="目标 Beta:").grid(row=10, column=0, sticky='w')
        self.target_beta = ttk.Entry(self.root)
        self.target_beta.grid(row=10, column=1, padx=10, pady=5)

        self.calculate_btn = ttk.Button(self.root, text="计算期货合约数量", command=self.calculate_futures)
        self.calculate_btn.grid(row=11, column=0, columnspan=2, pady=10)

        self.futures_result_label = ttk.Label(self.root, text="期货合约数量将显示在这里")
        self.futures_result_label.grid(row=12, column=0, columnspan=2, pady=10)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel文件", "*.xlsx")])
        if not file_path:
            return

        try:
            # 读取数据时强制基金代码为字符串类型
            self.fund_data = pd.read_excel(
                file_path,
                sheet_name=0,
                dtype={'基金代码': str}  # 修复前导零丢失问题
            )
            self.market_data = pd.read_excel(file_path, sheet_name=1)

            # 处理日期格式
            self.fund_data['净值日期'] = pd.to_datetime(self.fund_data['净值日期'])
            self.market_data['日期'] = pd.to_datetime(self.market_data['日期'])

            # 去重排序
            self.fund_data = self.fund_data.sort_values('净值日期').drop_duplicates()
            self.market_data = self.market_data.sort_values('日期').drop_duplicates()

            # 更新下拉菜单
            self.fund_code['values'] = sorted(self.fund_data['基金代码'].unique().tolist())
            dates = self.fund_data['净值日期'].dt.strftime('%Y/%m/%d').unique().tolist()
            self.start_date['values'] = dates
            self.end_date['values'] = dates

        except Exception as e:
            self.result_label.config(text=f"文件读取错误：{str(e)}")

    def analyze(self):
        # 重置结果
        self.result_label.config(text="计算中...")
        self.figure.clear()

        try:
            # 基础检查
            if self.fund_data is None or self.market_data is None:
                raise ValueError("请先加载数据文件")

            code = self.fund_code.get()
            if not code:
                raise ValueError("请选择基金代码")

            start_str = self.start_date.get()
            end_str = self.end_date.get()
            if not start_str or not end_str:
                raise ValueError("请选择日期范围")

            # 转换日期
            start = datetime.strptime(start_str, '%Y/%m/%d')
            end = datetime.strptime(end_str, '%Y/%m/%d')

            # 筛选基金数据
            fund_sub = self.fund_data[
                (self.fund_data['基金代码'] == code) &
                (self.fund_data['净值日期'] >= start) &
                (self.fund_data['净值日期'] <= end)
                ].copy()

            if fund_sub.empty:
                raise ValueError("选择的日期范围内没有该基金数据")

            # 计算基金收益率
            fund_sub['基金收益率'] = fund_sub['累计净值'].pct_change()
            fund_sub = fund_sub.dropna(subset=['基金收益率'])

            if fund_sub.empty:
                raise ValueError("收益率计算后无有效数据（至少需要两个数据点）")

            # 合并市场数据
            merged = pd.merge(
                fund_sub[['净值日期', '基金收益率']],
                self.market_data[['日期', 'hs300收益率', '无风险收益率']],
                left_on='净值日期',
                right_on='日期',
                how='inner'
            )

            if merged.empty:
                raise ValueError("合并后无匹配的日期数据（请检查市场数据日期范围）")

            # 计算超额收益率
            merged['无风险收益率'] = merged['无风险收益率'] / 100
            merged['无风险收益率'] = (1 + merged['无风险收益率']) ** (1 / 360) - 1  # 年化转日利率
            merged['基金超额收益率'] = merged['基金收益率'] - merged['无风险收益率']
            merged['市场超额收益率'] = merged['hs300收益率'] - merged['无风险收益率']
            merged = merged.dropna()

            if merged.empty:
                raise ValueError("超额收益率计算后无有效数据")

            # OLS回归
            X = sm.add_constant(merged['市场超额收益率'])
            model = sm.OLS(merged['基金超额收益率'], X).fit()
            self.current_beta = model.params[1]  # 将当前 Beta 保存为实例变量

            # 绘图
            ax = self.figure.add_subplot(111)
            ax.scatter(
                merged['市场超额收益率'],
                merged['基金超额收益率'],
                label='实际数据点',
                alpha=0.6
            )
            ax.plot(
                merged['市场超额收益率'],
                model.predict(X),
                color='red',
                linewidth=2,
                label='回归线'
            )
            ax.set_xlabel('市场超额收益率', fontsize=10)
            ax.set_ylabel('基金超额收益率', fontsize=10)
            ax.set_title('CAPM回归分析', fontsize=12)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend()
            self.canvas.draw()

            # 显示结果
            beta = model.params[1]
            r2 = model.rsquared
            p_value = model.pvalues[1]
            sig = "在5%的显著性水平下显著" if p_value < 0.05 else "在5%的显著性水平下不显著"
            result_text = (
                f"Beta系数: {beta:.8f}\n"
                f"R²: {r2:.8f}\n"
                f"显著性: {sig} (p={p_value:.8f})"
            )
            self.result_label.config(text=result_text)

        except Exception as e:
            self.result_label.config(text=f"错误：{str(e)}")
            self.canvas.draw()

    def create_chart_window(self, title):
        """创建新图表窗口的通用方法"""
        new_window = tk.Toplevel(self.root)
        new_window.title(title)
        fig = plt.Figure(figsize=(8, 4))
        canvas = FigureCanvasTkAgg(fig, master=new_window)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return fig, canvas

    def show_fund_chart(self):
        """显示基金累计净值和日收益率走势"""
        try:
            if self.fund_data is None:
                raise ValueError("请先加载数据文件")

            code = self.fund_code.get()
            if not code:
                raise ValueError("请选择基金代码")

            start_str = self.start_date.get()
            end_str = self.end_date.get()
            if not start_str or not end_str:
                raise ValueError("请选择日期范围")

            start = datetime.strptime(start_str, '%Y/%m/%d')
            end = datetime.strptime(end_str, '%Y/%m/%d')

            # 筛选基金数据
            fund_sub = self.fund_data[
                (self.fund_data['基金代码'] == code) &
                (self.fund_data['净值日期'] >= start) &
                (self.fund_data['净值日期'] <= end)
                ].sort_values('净值日期')

            if fund_sub.empty:
                raise ValueError("选择的日期范围内没有该基金数据")

            # 计算日收益率
            fund_sub = fund_sub.assign(
                日收益率=fund_sub['累计净值'].pct_change()
            )

            # 创建新窗口
            fig, canvas = self.create_chart_window(f"基金{code}走势分析")
            ax = fig.add_subplot(111)

            # 主坐标轴：累计净值
            ax.plot(fund_sub['净值日期'], fund_sub['累计净值'],
                    'b-', label='累计净值')
            ax.set_xlabel('日期')
            ax.set_ylabel('累计净值', color='b')
            ax.tick_params(axis='y', labelcolor='b')

            # 次坐标轴：日收益率
            ax1 = ax.twinx()
            ax1.plot(fund_sub['净值日期'], fund_sub['日收益率'],
                     'r--', label='日收益率')
            ax1.set_ylabel('日收益率', color='r')
            ax1.tick_params(axis='y', labelcolor='r')
            ax1.set_ylim(-0.05, 0.05)  # 设置收益率坐标范围

            # 图表装饰
            ax.set_title(f"基金{code}走势分析 ({start_str} 至 {end_str})")
            ax.grid(True)
            ax.legend(loc='upper left')
            ax1.legend(loc='upper right')
            fig.autofmt_xdate()

            canvas.draw()

        except Exception as e:
            self.result_label.config(text=f"错误：{str(e)}")

    def show_hs300_chart(self):
        """显示HS300日收益率走势"""
        try:
            if self.market_data is None:
                raise ValueError("请先加载数据文件")

            # 获取日期范围
            start_str = self.start_date.get()
            end_str = self.end_date.get()
            if not start_str or not end_str:
                raise ValueError("请选择日期范围")

            start = datetime.strptime(start_str, '%Y/%m/%d')
            end = datetime.strptime(end_str, '%Y/%m/%d')

            # 筛选数据
            market_sub = self.market_data[
                (self.market_data['日期'] >= start) &
                (self.market_data['日期'] <= end)
                ].sort_values('日期')

            if market_sub.empty:
                raise ValueError("选择的日期范围内没有市场数据")

            # 创建新窗口
            fig, canvas = self.create_chart_window("HS300日收益率走势")
            ax = fig.add_subplot(111)

            # 绘制收益率折线图
            ax.plot(market_sub['日期'], market_sub['hs300收益率'],
                    'g-', linewidth=1, label='HS300日收益率')
            ax.axhline(0, color='gray', linestyle='--', linewidth=0.5)

            # 图表装饰
            ax.set_title(f"HS300日收益率走势 ({start_str} 至 {end_str})")
            ax.set_xlabel('日期')
            ax.set_ylabel('日收益率')
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.autofmt_xdate()

            canvas.draw()

        except Exception as e:
            self.result_label.config(text=f"错误：{str(e)}")
        except Exception as e:
            self.result_label.config(text=f"错误：{str(e)}")

    # 用于计算期货合约数量
    def calculate_futures(self):
        try:
            # 获取输入值
            portfolio_value = float(self.portfolio_value.get())
            futures_price = float(self.futures_price.get())
            contract_multiplier = float(self.contract_multiplier.get())
            target_beta = float(self.target_beta.get())

            # 获取当前 Beta
            if not hasattr(self, 'current_beta'):
                raise ValueError("请先进行CAPM分析以获取当前Beta")

            current_beta = self.current_beta

            # 计算对冲比率
            hedge_ratio = current_beta - target_beta

            # 计算期货合约数量
            futures_contracts = (portfolio_value * hedge_ratio) / (futures_price * contract_multiplier)
            futures_contracts_rounded = round(futures_contracts, 8)

            # 显示结果
            if futures_contracts_rounded > 0:
                result_text = f"需要卖出 {futures_contracts_rounded} 手期货合约"
            elif futures_contracts_rounded < 0:
                result_text = f"需要买入 {abs(futures_contracts_rounded)} 手期货合约"
            else:
                result_text = "无需进行对冲操作"

            self.futures_result_label.config(text=result_text)

        except ValueError as e:
            self.futures_result_label.config(text=f"错误：{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CAPMAnalysisApp(root)
    root.mainloop()