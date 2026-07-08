Page({
  data: {
    inputDeviceId: "",
    deviceId: "",
    bindTime: ""
  },
  onLoad() {
    // 页面加载读取本地缓存已绑定设备
    const bindInfo = wx.getStorageSync('deviceBindInfo');
    if (bindInfo) {
      this.setData({
        deviceId: bindInfo.deviceId,
        bindTime: bindInfo.bindTime
      })
    }
  },
  // 实时监听输入框
  onInputDeviceId(e) {
    this.setData({
      inputDeviceId: e.detail.value.trim()
    })
  },
  // 清空输入框
  clearInput() {
    this.setData({ inputDeviceId: "" })
  },
  // 绑定设备
  bindDevice() {
    const devId = this.data.inputDeviceId;
    if (!devId) {
      wx.showToast({ title: "请输入设备编号", icon: "none" });
      return;
    }
    // 弹窗确认绑定
    wx.showModal({
      title: "确认绑定设备",
      content: `即将绑定设备：${devId}，绑定后将接收该设备所有健康数据与跌倒告警`,
      confirmText: "确认绑定",
      success: (res) => {
        if (res.confirm) {
          const nowTime = new Date().getFullYear() + "-" + (new Date().getMonth() + 1) + "-" + new Date().getDate() + " " + new Date().getHours() + ":" + new Date().getMinutes();
          const bindData = {
            deviceId: devId,
            bindTime: nowTime
          };
          // 存入本地缓存持久化
          wx.setStorageSync('deviceBindInfo', bindData);
          this.setData({
            deviceId: devId,
            bindTime: nowTime,
            inputDeviceId: ""
          })
          wx.showToast({ title: "设备绑定成功", icon: "success" });
        }
      }
    })
  },
  // 解除绑定
  unBindDevice() {
    wx.showModal({
      title: "解除设备绑定",
      content: "解绑后将不再接收该设备心率、跌倒告警等数据，确定解除？",
      confirmText: "确认解绑",
      confirmColor: "#ff3b30",
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('deviceBindInfo');
          this.setData({
            deviceId: "",
            bindTime: ""
          })
          wx.showToast({ title: "已解除绑定", icon: "success" });
        }
      }
    })
  }
})