Page({
  data: {
    content: '',          // 提醒输入内容
    selectTime: "08:00",  // 默认选中时间
    // 自定义提醒数组，每条结构：{id, content, time, checked, x:0}
    remindList: []
  },

  onShow() {
    // 页面打开读取本地缓存，数据持久化
    let list = wx.getStorageSync('remindList') || [];
    this.setData({ remindList: list });
  },

  // 输入框绑定内容
  inputChange(e) {
    this.setData({ content: e.detail.value })
  },

  // 时间选择器切换时分
  timeChange(e) {
    this.setData({ selectTime: e.detail.value })
  },

  // 新增提醒并存入本地缓存
  addRemind() {
    const content = this.data.content.trim()
    const time = this.data.selectTime
    if (!content) {
      wx.showToast({ title: '请输入提醒内容', icon: 'none' })
      return
    }
    // 构造新提醒对象，x=0 默认不滑动
    const newItem = {
      id: Date.now(), // 唯一ID
      content,
      time,
      checked: true,
      x: 0
    }
    const newList = [...this.data.remindList, newItem]
    this.setData({
      remindList: newList,
      content: '' // 清空输入框
    })
    // 持久化存入缓存
    wx.setStorageSync('remindList', newList)
    wx.showToast({ title: '添加成功' })
  },

  // 左滑松手处理：滑动距离超过阈值保持展开，否则收回
  slideEnd(e) {
    const index = e.currentTarget.dataset.index;
    const x = e.detail.x;
    const list = this.data.remindList;
    // 滑动超过-150rpx 保持删除按钮展开，否则收回
    list[index].x = x < -150 ? -180 : 0;
    this.setData({ remindList: list });
  },

  // 删除指定提醒
  delRemind(e) {
    const index = e.currentTarget.dataset.index;
    const list = this.data.remindList;
    list.splice(index, 1);
    this.setData({ remindList: list });
    wx.setStorageSync('remindList', list);
    wx.showToast({ title: '已删除' })
  },

  // 开关切换状态并同步缓存
  switchChange(e) {
    const index = e.currentTarget.dataset.index;
    const checked = e.detail.value;
    const list = this.data.remindList;
    list[index].checked = checked;
    this.setData({ remindList: list });
    wx.setStorageSync('remindList', list);
  }
})