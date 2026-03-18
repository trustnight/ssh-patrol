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
    
    # 加密标记前缀，用于识别已加密的文本
    ENCRYPTED_PREFIX = "ENC:"
    
    def __init__(self, secret_key=None):
        """初始化加密工具
        
        Args:
            secret_key: 密钥，如果为None则使用默认密钥
        """
        if secret_key is None:
            secret_key = self._generate_default_key()
        
        # 使用 SHA256 生成 32 字节密钥
        self.key = hashlib.sha256(str(secret_key).encode()).digest()
    
    def _generate_default_key(self):
        """生成默认密钥（基于机器特征）"""
        import platform
        machine_info = f"{platform.node()}-{platform.machine()}"
        return hashlib.sha256(machine_info.encode()).hexdigest()
    
    def encrypt(self, plaintext):
        """加密明文
        
        Args:
            plaintext: 明文字符串
        
        Returns:
            加密后的字符串（带ENC:前缀的Base64编码）
        """
        if not plaintext:
            return ""
        
        # 如果已经加密，直接返回
        if self.is_encrypted(plaintext):
            return plaintext
        
        try:
            # 生成随机 IV
            iv = os.urandom(16)
            
            # 创建 AES 加密器
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # 填充数据（PKCS7）
            data = plaintext.encode('utf-8')
            padding_length = 16 - (len(data) % 16)
            padded_data = data + bytes([padding_length] * padding_length)
            
            # 加密
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            
            # 组合 IV 和密文，然后进行 Base64 编码
            result = base64.b64encode(iv + encrypted).decode('utf-8')
            
            # 添加前缀标记
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
        
        # 如果不是加密格式，直接返回
        if not self.is_encrypted(ciphertext):
            return ciphertext
        
        try:
            # 移除前缀
            encrypted_data = ciphertext[len(self.ENCRYPTED_PREFIX):]
            
            # Base64 解码
            data = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # 分离 IV 和密文
            iv = data[:16]
            encrypted = data[16:]
            
            # 创建 AES 解密器
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            # 解密
            decrypted = decryptor.update(encrypted) + decryptor.finalize()
            
            # 去除填充（PKCS7）
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


# 创建全局加密工具实例
crypto = CryptoUtils()
