const util = require('../../utils/util.js');
// 小程序标准引入wx-charts，不要用import
const wxCharts = require('../../utils/wxcharts/wxcharts.js');
Page({
    /**
     * 页面的初始数据
     */
    data: {
        elderName: "张爷爷",
        deviceId: "RK3588_001",
        time: "暂无数据，请先获取Token同步设备",
        temp: "--",
        heart_rate: "--",
        spo2: "--",
        step: "--",
        lat: 28.2300,
        lng: 112.9300,
        timerId: null,        // 首页10秒UI刷新定时器
        iotTimer: null,       // IoT轮询定时器
        result: '等待获取token',
        fall: 0,    // 跌倒标识 0正常 1摔倒
        person: "",   // 家属标识
        // 心率图表相关
        lineChartHeart: null, // 心率图表实例
        heartData: [],        // 心率数值数组
        timeData: []          // X轴时间标签数组
    },
    // 定时轮询任务ID
    intervalId: null,

    /**
     * 获取token按钮按下
     */
    touchBtn_gettoken: function () {
        console.log("获取token按钮按下");
        this.setData({
            result: "获取token按键按下"
        });
        this.gettoken();
    },
    /**
     * 手动拉取设备影子
     */
    touchBtn_getshadow: function () {
        console.log("手动拉取设备影子按钮按下");
        this.setData({
            result: '手动同步设备数据中...'
        });
        this.getshadow();
    },
    /**
     * 下发设备指令
     */
    touchBtn_setCommand: function () {
        console.log("下发设备控制指令");
        this.setData({ result: '正在下发设备控制指令...' });
        this.setCommand();
    },

    /**
     * 获取华为IoT Token
     */
    gettoken: function () {
        console.log("开始获取Token");
        var that = this;
        wx.request({
            url: 'https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens',
            data: '{"auth":{"identity":{"methods":["password"],"password":{"user":{"name":"mmmmmm","password":"Qiansai666","domain":{"name":"hid_ce-mdhdff-vfwuw"}}}},"scope":{"project":{"name":"cn-north-4"}}}}',
            method: 'POST',
            header: { 'content-type': 'application/json' },
            success: function (res) {
                var token = JSON.stringify(res.header['X-Subject-Token']);
                token = token.replaceAll("\"", "");
                wx.setStorageSync('token', token);
                that.setData({ result: "Token获取成功：" + token.substring(0, 40) + "..." });
            },
            fail: function () {
                console.log("获取token失败");
                that.setData({ result: "Token获取失败，请核对账号密码！" })
            },
            complete: function () {
                console.log("获取token完成");
            }
        });
    },

    /**
     * 下发设备控制指令
     */
    setCommand: function () {
        var that = this;
        var token = wx.getStorageSync('token');
        if (!token) {
            that.setData({ result: "无Token，指令下发失败！" });
            return;
        }
        wx.request({
            url: 'https://12e17729f9.st1.iotda-app.cn-north-4.myhuaweicloud.com/v5/iot/019f279e355177b4bebb001f6a333677/devices/6a47a1c8cbb0cf6bb96b8ca9_1111/commands',
            data: '{"service_id": "chanpin1","command_name": "ON_OFF","paras": { "value": "ON"}}',
            method: 'POST',
            header: { 'content-type': 'application/json', 'X-Auth-Token': token },
            success: function () {
                that.setData({ result: "设备指令下发成功" });
            },
            fail: function () {
                that.setData({ result: "指令下发失败，请核对服务ID" })
            }
        })
    },

    /**
     * 拉取设备影子核心方法
     */
    getshadow: function () {
        console.log("开始获取设备影子");
        var that = this;
        var token = wx.getStorageSync('token');
        if (!token) {
            that.setData({ result: "无Token，请先点击获取鉴权令牌！" })
            return;
        }
        wx.request({
            url: 'https://12e17729f9.st1.iotda-app.cn-north-4.myhuaweicloud.com/v5/iot/019f279e355177b4bebb001f6a333677/devices/6a47a1c8cbb0cf6bb96b8ca9_1111/shadow',
            method: 'GET',
            header: { 'content-type': 'application/json', 'X-Auth-Token': token },
            success: function (res) {
                var reportData = res.data.shadow[0].reported.properties;
                var temp = reportData.temp ?? "--";
                var heart_rate = reportData.heart_rate ?? "--";
                var spo2 = reportData.spo2 ?? "--";
                var step = reportData.step ?? "--";
                var fall = reportData.fall ?? 0;
                var person = reportData.person ?? "";
                var lat = reportData.lat ?? 28.2300;
                var lng = reportData.lng ?? 112.9300;
                var eventTimeStr = res.data.shadow[0].reported.event_time;
                var updateTime = util.formatTime(new Date());

                // 格式化采集时间（X轴标签）
                var formattedEventTime = eventTimeStr.replace(/(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z/, '$1-$2-$3 $4:$5');
                var validHeart = parseFloat(heart_rate);
                if (isNaN(validHeart)) validHeart = 0;

                // 处理心率历史数组，最多保留20条
                var heartArr = [...that.data.heartData];
                var timeArr = [...that.data.timeData];
                if (!isNaN(validHeart) && validHeart > 0) {
                    heartArr.push(validHeart);
                    timeArr.push(formattedEventTime);
                    if (heartArr.length > 20) {
                        heartArr.shift();
                        timeArr.shift();
                    }
                }

                that.setData({
                    temp, heart_rate, spo2, step, fall, person, lat, lng,
                    time: updateTime,
                    heartData: heartArr,
                    timeData: timeArr,
                    result: `同步成功｜体温${temp}℃ 心率${heart_rate}次/分 血氧${spo2}% 步数${step} 跌倒${fall} 陪伴：${person||"无"}`
                });

                // 跌倒本地弹窗告警
                if (Number(fall) === 1) {
                    wx.showModal({
                        title: "⚠️ 跌倒紧急告警",
                        content: `${that.data.elderName} 老人已触发跌倒监测，请立即查看！`,
                        confirmText: "一键呼叫120",
                        cancelText: "稍后查看",
                        confirmColor: "#ff3b30",
                        success(res) {
                            if (res.confirm) wx.makePhoneCall({ phoneNumber: "120" })
                        }
                    })
                }

                // 首次创建图表实例
                if (!that.data.lineChartHeart) {
                    const windowInfo = wx.getWindowInfo();
                    const chartWidth = windowInfo.windowWidth * 0.84;
                    that.setData({
                        lineChartHeart: new wxCharts({
                            canvasId: 'heartLineChart',
                            type: 'line',
                            width: chartWidth,
                            height: 320,
                            dataLabel: true,
                            dataPointShape: true,
                            xAxis: {
                                categories: timeArr,
                                gridColor: '#eee'
                            },
                            yAxis: {
                                title: '心率(次/分)',
                                min: 50,
                                max: 90,
                                gridColor: '#eee'
                            },
                            series: [{
                                name: '实时心率',
                                data: heartArr,
                                stroke: '#ff3b30',
                                fill: false,
                                lineWidth: 3,
                                format: function (val) {
                                    return val.toFixed(0);
                                }
                            }],
                            background: '#f8f8f8',
                            legend: { show: false }
                        })
                    })
                } else {
                    // 已有实例，动态更新曲线数据
                    that.updateChart();
                }
            },
            fail: function () {
                console.log("获取影子失败");
                that.setData({ result: "获取设备影子失败，Token失效或设备离线！" })
            },
            complete: function () {
                console.log("获取影子完成");
            }
        });
    },

    /**
     * 更新图表数据（和你PH/浑浊度逻辑完全一致）
     */
    updateChart: function () {
        var heartChart = this.data.lineChartHeart;
        if (heartChart) {
            heartChart.updateData({
                categories: this.data.timeData,
                series: [{
                    name: '实时心率',
                    data: this.data.heartData,
                    format: function (val) {
                        return val.toFixed(0);
                    }
                }]
            });
        }
    },

    // 开启2秒轮询实时拉取数据
    startIotLoop: function () {
        if (this.data.iotTimer) clearInterval(this.data.iotTimer);
        const timer = setInterval(() => {
            this.getshadow();
        }, 2000);
        this.setData({ iotTimer: timer });
    },
    stopIotLoop: function () {
        if (this.data.iotTimer) {
            clearInterval(this.data.iotTimer);
            this.setData({ iotTimer: null });
        }
    },

    // 页面全局10秒刷新
    refreshAllPage() {
        const nowTime = util.formatTime(new Date());
        const cacheData = wx.getStorageSync("elderHealth");
        if (cacheData) {
            this.setData({
                elderName: cacheData.elderName,
                deviceId: cacheData.deviceId,
                time: nowTime,
                temp: cacheData.temp,
                heart_rate: cacheData.heart_rate,
                spo2: cacheData.spo2,
                step: cacheData.step,
                fall: cacheData.fall,
                person: cacheData.person,
                lat: cacheData.lat,
                lng: cacheData.lng
            })
        } else {
            this.setData({
                elderName: "张爷爷",
                deviceId: "RK3588_001",
                time: "暂无数据，请先获取Token同步设备",
                temp: "--",
                heart_rate: "--",
                spo2: "--",
                step: "--",
                fall: 0,
                person: "",
                lat: 28.2300,
                lng: 112.9300
            })
        }
    },
    startFullRefreshTimer() {
        if (this.data.timerId) clearInterval(this.data.timerId);
        const timer = setInterval(() => this.refreshAllPage(), 10000);
        this.setData({ timerId: timer });
    },
    stopTimer() {
        if (this.data.timerId) {
            clearInterval(this.data.timerId);
            this.setData({ timerId: null });
        }
    },

    /**
     * 生命周期
     */
    onLoad(options) {
        this.gettoken();
    },
    onShow() {
        this.refreshAllPage();
        this.startFullRefreshTimer();
        this.startIotLoop();
    },
    onHide() {
        this.stopTimer();
        this.stopIotLoop();
    },
    onUnload() {
        this.stopTimer();
        this.stopIotLoop();
    },

    // 页面跳转、120呼叫
    call120() {
        wx.makePhoneCall({ phoneNumber: "120" })
    },
    goVoice() { wx.navigateTo({ url: '/pages/voice/voice' }) },
    goRemind() { wx.navigateTo({ url: '/pages/remind/remind' }) },
    goDevice() {wx.navigateTo({ url:'/pages/device/device' }) },
    goMine() { wx.navigateTo({ url: '/pages/mine/mine' }) }
})