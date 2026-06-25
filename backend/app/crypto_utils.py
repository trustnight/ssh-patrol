# -*- coding: utf-8 -*-
"""
加密/解密工具模块
使用 AES 加密，输出更短的密文
"""
import base64
import hashlib
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class CryptoUtils:
    """加密/解密工具类"""

    ENCRYPTED_PREFIX = "ENC:"

    def __init__(self, secret_key=None):
        """初始化加密工具

        Args:
            secret_key: 密钥，如果为None则使用默认密钥
        """
        if secret_key is None:
            secret_key = self._generate_default_key()

        self.key = hashlib.sha256(str(secret_key).encode()).digest()

    def _generate_default_key(self):
        """生成默认密钥"""
        return "xunjian-helper-secret-key-2024"

    def encrypt(self, plaintext):
        """加密明文

        Args:
            plaintext: 明文字符串

        Returns:
            加密后的字符串（带ENC:前缀的Base64编码）
        """
        if not plaintext:
            return ""

        if self.is_encrypted(plaintext):
            return plaintext

        try:
            iv = os.urandom(16)

            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            data = plaintext.encode('utf-8')
            padding_length = 16 - (len(data) % 16)
            padded_data = data + bytes([padding_length] * padding_length)

            encrypted = encryptor.update(padded_data) + encryptor.finalize()

            result = base64.b64encode(iv + encrypted).decode('utf-8')

            return self.ENCRYPTED_PREFIX + result

        except Exception as e:
            print(f"加密失败: {e}")
            return plaintext

    def decrypt(self, ciphertext):
        """解密密文

        Args:
            ciphertext: 加密的字符串（带ENC:前缀）

        Returns:
            解密后的明文字符串
        """
        if not ciphertext:
            return ""

        if not self.is_encrypted(ciphertext):
            return ciphertext

        try:
            encrypted_data = ciphertext[len(self.ENCRYPTED_PREFIX):]

            data = base64.b64decode(encrypted_data.encode('utf-8'))

            iv = data[:16]
            encrypted = data[16:]

            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()

            decrypted = decryptor.update(encrypted) + decryptor.finalize()

            padding_length = decrypted[-1]
            decrypted = decrypted[:-padding_length]

            return decrypted.decode('utf-8')

        except Exception as e:
            print(f"解密失败: {e}")
            return ""

    def is_encrypted(self, text):
        """检查文本是否已加密

        Args:
            text: 要检查的文本

        Returns:
            bool: True表示已加密，False表示未加密
        """
        if not text:
            return False

        return text.startswith(self.ENCRYPTED_PREFIX)


crypto = CryptoUtils()
