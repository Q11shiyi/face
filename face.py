import logging
import os
import time
import uuid

import face_recognition
import pymysql
from flask import Flask, request, jsonify, redirect

# 第一步，创建一个logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Log等级总开关

# 第二步，创建一个handler，用于写入日志文件
rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))[:-4]

log_path = 'log/'
log_name = log_path + rq + '.log'
fh = logging.FileHandler(log_name, mode='a')
fh.setLevel(logging.DEBUG)  # 输出到file的log等级的开关

# 第三步，定义handler的输出格式
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
fh.setFormatter(formatter)

# 第四步，将logger添加到handler里面
logger.addHandler(fh)
app = Flask(__name__)


# 人脸上传
@app.route('/faceUpload', methods=['POST'])
def upload_image():
    if request.method == 'POST':
        fname = request.files.get('file')
        filename = str(uuid.uuid1())

        # 第二个参数为返回Java的相对路径
        list = detect_faces_in_image(fname, "/archiveFile/image/" + filename + '.jpg')

        if len(list) != 0:
            logger.info("识别人脸，保存图片")
            # basename = os.path.dirname(__file__)  # 当前文件所在路径
            upload_path = 'F:/archiveFile/image/'+filename + '.jpg'
            fname.seek(0)
            print(upload_path)
            fname.save(upload_path)
        result = {
            "code": "200",
            "msg": "upload success",
            "totalFace": list
        }
        return jsonify(result)


def detect_faces_in_image(file_stream, upload_path):
    # 载入用户上传的图片
    img = face_recognition.load_image_file(file_stream)
    # 为用户上传的图片中的人脸编码
    face_encodings = face_recognition.face_encodings(img, num_jitters=100)
    locations = face_recognition.face_locations(img)
    list = []
    for i in range(len(face_encodings)):
        face = {
            "imagePath": upload_path,
            "faceLocation": locations[i],
            "faceEncoding": face_encodings[i].tolist()
        }
        list.append(face)
    print("总共有", len(face_encodings), "张人脸")
    return list


# 人脸搜索
@app.route('/faceSearch', methods=['GET', 'POST'])
def search_image():
    # 检测图片是否上传成功
    if request.method == 'POST':
        # 获取相似度参数
        # s = request.args['str']
        s = request.form.get('str')
        if s is None:
            s = 60
        print(type(s), (100 - int(s)) / 100)
        s = (100 - int(s)) / 100
        print(s)
        # 判断是否是文件
        if 'file' not in request.files:
            return redirect(request.url)

        fname = request.files['file']
        # 图片上传成功，检测图片中的人脸
        # 载入用户上传的图片
        img = face_recognition.load_image_file(fname)
        face_recognition.face_distance()
        # 为用户上传的图片进行编码
        face_encodings = face_recognition.face_encodings(img)

        # 查询出数据库全部人脸编码
        sql = "select f.face_id,f.file_id,f.face_encoding,f.image_path,af.fileName,af.information,af.createTime,af.updateTime from face f inner join archive_files af on f.file_id = af.id"
        logger.info("检索：图片中包含有" + str(len(face_encodings)) + "张人脸")
        li = []
        imagePath = []
        try:
            # 打开数据库连接
            db = pymysql.connect("192.168.0.146", "root", "root", "archive", charset='utf8')
            # 使用cursor()方法获取操作游标
            db.ping(True)
            cursor = db.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            # 遍历数据库人脸数据
            for index in range(len(face_encodings)):
                for re in results:
                    # 将数组转成 list
                    mysql_face = list(eval(re[2]))
                    # 进行逐个比对 1.已知人脸 2.未知人脸 3.容忍度
                    match_results = face_recognition.compare_faces([mysql_face], face_encodings[index], s)
                    if match_results[0]:
                        # 图片人脸 多对多 判断是否存在相同人脸
                        li1 = face_recognition.face_distance([mysql_face], face_encodings[index])
                        # 小数转换成百分比
                        le = (1 - li1[0]) * 100
                        face = {
                            "faceId": re[0],
                            "fileId": re[1],
                            "faceSimilarity": '%d%%' % le,
                            "imagePath": re[3],
                            "fileName": re[4],
                            "information": re[5],
                            "createTime": re[6],
                            "updateTime": re[7],
                        }

                        li.append(face)

            print(type(li))
            # 去除相同的人脸 不改变集合顺序
            # faceList = sorted(set(li), key=li.index)
        except IOError:
            print(IOError.filename)
        print(li)
        # qw = sorted(set(imagePath), key=f.get('image_id'))
        # 如果存在多张人脸 根据image_id去除相同图片
        l2 = []
        for i in li:
            if not i in l2:
                l2.append(i)
        result = {
            "code": 200,
            "message": "检索成功",
            "data": l2
        }
        logger.info('比对成功' + str(len(l2)) + '张图片')
        return jsonify(result)


if __name__ == "__main__":
    app.config['JSON_AS_ASCII'] = False
    app.run(host='0.0.0.0', port=5006, debug=True, threaded=True)
