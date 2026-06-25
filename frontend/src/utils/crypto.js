import CryptoJS from 'crypto-js'

const ENCRYPTED_PREFIX = 'ENC:'
const SECRET_KEY = 'xunjian-helper-secret-key-2024'

function deriveKey(secretKey) {
  return CryptoJS.SHA256(secretKey || SECRET_KEY).toString(CryptoJS.enc.Hex)
}

export function encrypt(plaintext, secretKey = null) {
  if (!plaintext) return ''
  if (isEncrypted(plaintext)) return plaintext

  try {
    const keyHex = deriveKey(secretKey)
    const key = CryptoJS.enc.Hex.parse(keyHex)
    const iv = CryptoJS.lib.WordArray.random(16)

    const encrypted = CryptoJS.AES.encrypt(plaintext, key, {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    })

    const ivBase64 = CryptoJS.enc.Base64.stringify(iv)
    const ciphertextBase64 = encrypted.ciphertext.toString(CryptoJS.enc.Base64)

    const combined = CryptoJS.enc.Base64.parse(ivBase64).concat(
      CryptoJS.enc.Base64.parse(ciphertextBase64)
    )

    const result = combined.toString(CryptoJS.enc.Base64)

    return ENCRYPTED_PREFIX + result
  } catch (e) {
    console.error('加密失败:', e)
    return plaintext
  }
}

export function decrypt(ciphertext, secretKey = null) {
  if (!ciphertext) return ''
  if (!isEncrypted(ciphertext)) return ciphertext

  try {
    const keyHex = deriveKey(secretKey)
    const key = CryptoJS.enc.Hex.parse(keyHex)

    const encryptedData = ciphertext.substring(ENCRYPTED_PREFIX.length)
    const data = CryptoJS.enc.Base64.parse(encryptedData)

    const words = data.words
    const ivWords = words.slice(0, 4)
    const cipherWords = words.slice(4)

    const iv = CryptoJS.lib.WordArray.create(ivWords, 16)
    const cipherParams = CryptoJS.lib.CipherParams.create({
      ciphertext: CryptoJS.lib.WordArray.create(cipherWords, (words.length - 4) * 4)
    })

    const decrypted = CryptoJS.AES.decrypt(cipherParams, key, {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    })

    return decrypted.toString(CryptoJS.enc.Utf8)
  } catch (e) {
    console.error('解密失败:', e)
    return ''
  }
}

export function isEncrypted(text) {
  if (!text) return false
  return text.startsWith(ENCRYPTED_PREFIX)
}

export default {
  encrypt,
  decrypt,
  isEncrypted
}
