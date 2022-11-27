// Initialize the echarts instance based on the prepared dom
var myChart = echarts.init(document.getElementById('main_chart'));

// Specify the configuration items and data for the chart
var option = {
    title: {
        text: {
            // { recordTime[-1] | tojson }
        },
        subtext: 'Voltage L-N Average [V]' // localID 2
    },
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'cross'
        }
    },
    toolbox: {
        show: true,
        feature: {
            saveAsImage: {}
        }
    },
    xAxis: {
        type: 'category',
        boundaryGap: false,
        // prettier-ignore
        data: ['00:00', '01:15', '02:30', '03:45', '05:00', '06:15', '07:30', '08:45', '10:00', '11:15', '12:30', '13:45', '15:00', '16:15', '17:30', '18:45', '20:00', '21:15', '22:30', '23:45']
            // data: {
            //     { recordTime | tojson }
            // }
    },
    yAxis: {
        type: 'value',
        axisLabel: {
            formatter: '{value} V'
        },
        axisPointer: {
            snap: true
        }
    },
    visualMap: {
        show: false,
        dimension: 0,
        pieces: [{
                lte: 6,
                color: 'green'
            },
            {
                gt: 6,
                lte: 8,
                color: 'red'
            },
            {
                gt: 8,
                lte: 14,
                color: 'green'
            },
            {
                gt: 14,
                lte: 17,
                color: 'red'
            },
            {
                gt: 17,
                color: 'green'
            }
        ]
    },
    series: [{
        name: 'Electricity',
        type: 'line',
        smooth: true,
        // prettier-ignore
        data: [300, 280, 250, 260, 270, 300, 550, 500, 400, 390, 380, 390, 400, 500, 600, 750, 800, 700, 600, 400],
        // data: {
        //     { dataValue[1] | tojson }
        // },
        markArea: {
            itemStyle: {
                color: 'rgba(255, 173, 177, 0.4)'
            },

        }
    }]
};

// Display the chart using the configuration items and data just specified.
myChart.setOption(option);