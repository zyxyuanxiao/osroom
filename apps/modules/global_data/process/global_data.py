# -*-coding:utf-8-*-
from bson import ObjectId
from flask_babel import gettext
from flask_login import current_user
from apps.configs.sys_config import VERSION
from apps.utils.paging.paging import datas_paging
from apps.core.utils.get_config import get_configs, get_config
from apps.utils.upload.get_filepath import get_file_url
from flask import request
from apps.app import mdbs
from apps.utils.format.obj_format import json_to_pyseq, objid_to_str, str_to_num

__author__ = "Allen Woo"


def get_global_site_data(req_type="api"):
    """
    获取全局的站点信息
    req_type:如果为"view"则不需要返回用户基本信息
    :return:
    """
    data = {}

    # 全局数据
    # theme
    data["theme_config"] = get_configs("theme_global_conf")
    # site
    data["site_config"] = get_configs("site_config")
    data["site_config"] = dict(data["site_config"], **get_configs("seo"))
    data["site_config"]["sys_version"] = VERSION
    # msg
    if current_user.is_authenticated:
        msgs = mdbs["user"].db.message.find({"user_id": current_user.str_id,
                                         "$or": [{"status": "not_noticed"},
                                                 {"status": {"$exists": False}}]},
                                        {"_id": 0, "content": 0})
        msg_cnt = msgs.count(True)
        data["user_msg"] = {"msg_count": msg_cnt,
                            "msgs": list(msgs.sort([("time", -1)]))}
    if req_type != "view":
        if current_user.is_authenticated:
            user_info = objid_to_str(current_user.user_info, ["id", "role_id"])
            data["is_authenticated"] = True
            data["user_info"] = user_info
        else:
            data["is_authenticated"] = False
            data["user_info"] = {}

    data['d_msg'] = gettext("Get the current user information successfully")
    data['d_msg_type'] = "s"
    return data


def get_global_media(dbname, collname):
    """

    根据conditions, category_name
    获取media或theme_display_setting中的数据
    :param dbname:
    :param collname:
    :return:
    """
    mdb = mdbs[dbname]
    conditions = json_to_pyseq(request.argget.all("conditions", []))
    category_name = json_to_pyseq(request.argget.all("category_name", []))
    media_id = request.argget.all("media_id")

    medias = {}
    if collname == "theme_display_setting":
        q = {"theme_name": get_config("theme", "CURRENT_THEME_NAME")}
    else:
        q = {}

    if media_id:
        q["_id"] = ObjectId(media_id)
        media = mdb.dbs[collname].find_one(q)
        media["_id"] = str(media["_id"])
        media["url"] = get_file_url(media["url"])
        data = {"media": media}
        return data

    elif category_name and collname == "media":
        # collname == "media" 的时候
        # 获取指定category_name user_id type的media
        category_user_id = request.argget.all("category_user_id", 0)
        category_type = request.argget.all("category_type")
        page = str_to_num(request.argget.all("page", 1))
        pre = str_to_num(request.argget.all("pre", 8))

        categorys = mdbs["web"].db.category.find(
            {
                "type": category_type, "user_id": category_user_id, "name": {
                    "$in": category_name}}, {
                "_id": 1})

        category_ids = []
        for category in categorys:
            category_ids.append(str(category["_id"]))

        sort = [("time", -1)]

        q["category_id"] = {"$in": category_ids}
        medias = mdb.dbs[collname].find(q)

        data_cnt = medias.count(True)
        medias = list(medias.sort(sort).skip(pre * (page - 1)).limit(pre))
        for d in medias:
            d["_id"] = str(d["_id"])
            if "url" in d and d["url"]:
                d["url"] = get_file_url(d["url"])
        medias = datas_paging(
            pre=pre,
            page_num=page,
            data_cnt=data_cnt,
            datas=medias)
    else:
        for condition in conditions:
            if "name_regex" in condition and condition["name_regex"]:
                q["type"] = condition["type"]
                q["name"] = {"$regex": condition["name_regex"], "$options": "$i"}
                temp_media = list(mdb.dbs[collname].find(q).sort([("name", 1)]))
            else:
                q["type"] = condition["type"]
                q["name"] = {"$in": condition["names"]}

                temp_media = list(mdb.dbs[collname].find(q).sort([("name", 1)]))

            for d in temp_media:
                d["_id"] = str(d["_id"])
                if "url" in d and d["url"]:
                    d["url"] = get_file_url(d["url"])
            medias[condition["result_key"]] = temp_media
    data = {"medias": medias}
    return data
