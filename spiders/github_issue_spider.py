import logging
import re
import requests
import json
from pyquery import PyQuery
from urllib.parse import urljoin, urlparse
from models.model_issue import Issue

# 获取html页面文本
def get_url_page(url):
    response = requests.get(url)
    logging.info(response.status_code)

    if response.status_code == 200:
        return response.text


# 解析issue页，爬取页面的issue列表
def parse_issue_page(html, url, status):
    # 用于存储所有issue信息
    issue_list_per_page = list()

    # 实例化PyQuery对象
    document = PyQuery(html)

    # 过滤获取issue所有标签
    issue_all = document('div').filter('.js-issue-row')

    # items() 转化为list
    issue_items = issue_all.items()


    # 获取每一个issue
    for item in issue_items:
        head = item('a').filter('.h4')

        # issue信息项
        id     = re.findall(r"\d+", item.attr('id'))[0]
        title  = head.text()
        type   = item('.IssueLabel').text()
        link   = urljoin(url, head.attr('href'))
        time   = item('span').filter('.opened-by').children('relative-time').attr('datetime')
        author = item('.opened-by').filter('a').text()
        # 没有添加标签的类别，使用default代替
        if type == '':
            type = 'default'

        # 使用json类型保存
        item_info = {
            'id'      :  id,
            'source'  :  urlparse(url).path,
            'title'   :  title,
            'type'    :  type,
            'link'    :  link,
            'time'    :  time,
            'answered':  'no',
            'status'  :  status,
            'author'  :  author,
            'content' :  ''
        }
        issue_list_per_page.append(item_info)

    logging.info(issue_list_per_page)

    # 下一页链接
    next_page_link = document('.next_page').attr('href')
    logging.info(next_page_link)

    # 判断下一页链接是否disabled
    if next_page_link != None:
        next_page_link = urljoin(url, next_page_link)

    return issue_list_per_page, next_page_link


# 循环获取所有issue页面获取所有issue项, 返回issue list
def get_issues(url):
    base_url = url
    html = get_url_page(url)
    issue_list, next_page = parse_issue_page(html, url, 'opened')

    while next_page != None:
        html = get_url_page(next_page)
        issue_list_per_page, next_page = parse_issue_page(html, url, 'opened')
        issue_list += issue_list_per_page

    # 爬取已关闭的issue
    closed_url = base_url + '?q=is%3Aissue+is%3Aclosed'
    html = get_url_page(closed_url)
    temp_list, next_page = parse_issue_page(html, closed_url, 'closed')

    issue_list = temp_list

    while next_page != None:
        html = get_url_page(next_page)
        issue_list_per_page, next_page = parse_issue_page(html, closed_url, 'closed')
        issue_list += issue_list_per_page


    logging.info(issue_list)
    print(issue_list)
    return issue_list


# 获取单个issue的详情页评论信息
def get_issue_detail(issue_url):
    answered = 'no'
    html = get_url_page(issue_url)
    document = PyQuery(html)

    timeline = list()
    comments = document('.timeline-comment').items()

    issue_author = comments[0]('a').filter('author').text()

    for comment in comments:
        author = comment('a').filter('author').text()
        header = comment('.timeline-comment-header').text()
        timestamp = comment('.timeline-comment-header').children('relative-time').attr('datetime')
        comment_text = comment('table').text()
        comment_item = {
            'author'    : author,
            'header'    : header,
            'timestamp' : timestamp,
            'comment'   : comment_text
        }
        timeline.append(comment_item)

        if author != issue_author:
            answered = 'yes'

    logging.info(timeline)
    return timeline, answered


# 获取所有issue评论信息
def get_all_issues_detail(issue_list):
    issue_db = Issue()
    for issue in issue_list:
        timeline, answered = get_issue_detail(issue['link'])
        issue['answered'] = answered
        issue['content'] = json.dumps(timeline, ensure_ascii=False)
        print(issue)
        issue_db.save_one(issue)
    logging.info(issue_list)
    return issue_list
