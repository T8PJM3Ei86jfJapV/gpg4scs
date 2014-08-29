Sina Cloud Storage with GPG
===================

gpg4scs是基于新浪云存储（SCS）的加密云盘客户端，类似于Dropbox等网盘，它可以将本地数据跟云端进行同步。

由于所有数据都在本地采用GPG加密后再传送到云端，所以最大程度保护了数据安全性，适合需要高强度加密云存储的场合。程序使用python编写，支持Windows、Linux、MacOS平台。

在使用本工具前，你需要了解GnuPG、非对称加密等相关概念。

----------

依赖
-------------

1、Python 2.7
2、GnuPG

----------

配置
-------------------

1、使用GPG生成密钥，并将私钥放在主程序所在目录下，命名为```secret.asc```

2、使用新浪云存储并创建Bucket

3、配置profile.ini文件，参数说明：
local.path: 需要同步的本地目录，该目录及其各级子目录下的文件将与云端同步。
gpg.passphrase: GPG密钥密码，可以为空。


>  [sina-storage]
> accesskey = 1jsoemyEkCRTBOYRqAlE
> secretkey = f691cbe0ske5dfd79ac3fbccms6eoec5547f697b  
> buket = my-testing-bucket

> [local]
> path = /home/admin/Desktop/

> [gpg]
> passphrase = 1234567890

----------

使用
-------------------
1、仅上传：```python gpg4scs.py -u```
2、仅下载：```python gpg4scs.py -d```
3、文件同步：```python gpg4scs.py -s```
4、帮助：```python gpg4scs.py -h```

----------

已知Bug
-------------------
1、不支持中文路径和中文文件名
2、Linux下不支持带英文空格的路径或文件名
