const app = getApp();
Page({
  data: {
    elderName: app.globalData.elderName || '',
    // 替换原来固定的familyName，改为可输入字段
    relation: "",    // 与老人关系（子女/配偶/护工等）
    phone: ""        // 家属联系手机号
  },
  // 表单输入绑定
  inputRelation(e) {
    this.setData({
      relation: e.detail.value
    })
  },
  inputPhone(e) {
    this.setData({
      phone: e.detail.value
    })
  },
  // 保存关系和手机号到全局，方便其他页面调用
  saveFamilyInfo() {
    const { relation, phone } = this.data;
    if (!relation.trim()) {
      wx.showToast({ title: '请填写亲属关系', icon: 'none' })
      return;
    }
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      wx.showToast({ title: '手机号格式错误', icon: 'none' })
      return;
    }
    // 存入全局
    app.globalData.relation = relation;
    app.globalData.phone = phone;
    wx.showToast({ title: '保存成功' })
  },
  // 原有订阅消息函数完全不变
  subscribeMessage() {
    wx.requestSubscribeMessage({
      tmplIds: [
        'jJZ7J7xMS5vzabm8tpMXO1MO2rTj_eghiU4MDN_WASA'
      ],
      success(res) {
        console.log("订阅结果：", res)
      },
      fail(err) {
        console.log(err)
      }
    })
  },
  // 页面加载时读取全局已保存的信息，回填输入框
  onLoad() {
    this.setData({
      relation: app.globalData.relation || "",
      phone: app.globalData.phone || ""
    })
  }
});