/**
  useNetworkNotice - 网络环境与长篇音频流量感知
  根据 Network Information API 及经典篇幅，提供温润的流量使用感知与 Wi-Fi 建议
*/
import { ref } from 'vue'

export function useNetworkNotice() {
  const isCellular = ref(false)

  function checkConnection() {
    if (typeof navigator === 'undefined') return false
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection
    if (!conn) return false
    if (conn.type === 'cellular') return true
    if (conn.effectiveType && ['2g', '3g', '4g', 'slow-2g'].includes(conn.effectiveType)) {
      return true
    }
    if (conn.saveData === true) return true
    return false
  }

  try {
    isCellular.value = checkConnection()
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection
    if (conn && typeof conn.addEventListener === 'function') {
      conn.addEventListener('change', () => {
        isCellular.value = checkConnection()
      })
    }
  } catch (e) {}

  /**
   * 获取针对特定经典的流量提示信息
   * @param {string} bookId 
   * @returns {string|null} 提示文案，null 表示无需提示
   */
  function getTrafficNotice(bookId) {
    const isLongSutra = bookId === 'dizangjing'
    const cellular = isCellular.value

    if (cellular && isLongSutra) {
      return '当前处于移动蜂窝网络，长篇经文单品约 15MB，建议在 Wi-Fi 环境下持诵。'
    }
    if (cellular) {
      return '当前处于移动蜂窝网络，持诵音频将消耗移动流量。'
    }
    if (isLongSutra) {
      return '长篇经文音频单品约 15MB，建议在 Wi-Fi 环境下持诵。'
    }
    return null
  }

  return {
    isCellular,
    getTrafficNotice
  }
}
