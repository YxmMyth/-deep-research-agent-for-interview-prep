"""
图表生成工具
将 ECharts 配置转换为 HTML
"""


def generate_echarts_html(echarts_json: str, title: str = "技术栈分布") -> str:
    """
    生成包含 ECharts 图表的 HTML 页面

    Args:
        echarts_json: ECharts 配置 JSON 字符串
        title: 页面标题

    Returns:
        HTML 字符串
    """
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #333;
        }}
        #chart {{
            width: 100%;
            height: 600px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div id="chart"></div>
    </div>

    <script type="text/javascript">
        var chartDom = document.getElementById('chart');
        var myChart = echarts.init(chartDom);
        var option = {echarts_json};
        myChart.setOption(option);

        window.addEventListener('resize', function() {{
            myChart.resize();
        }});
    </script>
</body>
</html>"""

    return html_template
