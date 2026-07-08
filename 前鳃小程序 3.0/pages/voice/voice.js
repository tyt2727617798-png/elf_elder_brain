const util = require('../../utils/util.js');
Page({
  recorderManager: null,
  innerAudioContext: null, // 音频播放实例
  data: {
    recording: false, // 是否正在录音
  },

  onLoad() {
    // 初始化录音管理器
    this.recorderManager = wx.getRecorderManager();
    this.innerAudioContext = wx.createInnerAudioContext();

    // 监听录音结束回调，获取音频临时文件
    this.recorderManager.onStop((res) => {
      const tempFilePath = res.tempFilePath;
      console.log("录音文件路径：", tempFilePath);
      // 此处可写上传华为云/后端接口代码，上传音频文件
      wx.showModal({
        title: "录音完成",
        content: "语音已发送至老人设备终端",
        confirmText: "确定"
      })
      this.setData({ recording: false });
    })

    // 录音异常监听
    this.recorderManager.onError((err) => {
      wx.showToast({ title: "录音失败，请开启麦克风权限", icon: "none" })
      console.error("录音错误：", err);
      this.setData({ recording: false });
    })
  },

  // 按住开始录音
  startRecord() {
    if (this.data.recording) return;
    wx.getSetting({
      success: (res) => {
        // 校验麦克风权限
        if (!res.authSetting['scope.record']) {
          wx.authorize({
            scope: 'scope.record',
            success: () => {
              this.doStartRecord();
            },
            fail: () => {
              wx.showToast({ title: "请开启麦克风权限", icon: "none" })
            }
          })
        } else {
          this.doStartRecord();
        }
      }
    })
  },

  // 执行开始录音
  doStartRecord() {
    this.setData({ recording: true });
    wx.showToast({ title: '正在录音，松开发送', icon: 'none', duration: 10000 });
    this.recorderManager.start({
      format: 'mp3',
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 96000
    });
  },

  // 松开停止录音
  stopRecord() {
    if (!this.data.recording) return;
    wx.hideToast();
    this.recorderManager.stop();
  },

  // 快捷文字语音（模拟发送安抚文字语音，可对接TTS文字转语音接口）
  sendQuickVoice(e) {
    const text = e.currentTarget.dataset.text;
    wx.showLoading({ title: "正在发送语音..." });
    setTimeout(() => {
      wx.hideLoading();
      wx.showModal({
        title: "快捷语音已发送",
        content: `发送内容：${text}`,
        confirmText: "确认"
      })
      // 此处可对接后端TTS接口，文字转语音下发设备
    }, 800)
  },

  onUnload() {
    // 页面销毁停止录音、释放资源
    if (this.data.recording) this.recorderManager.stop();
    this.innerAudioContext.destroy();
  }
})