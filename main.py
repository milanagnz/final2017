# фласк
from flask import Flask
from flask import render_template, request
# работа с АПИ
import requests
import re
import html
# граф
import networkx as nx
import matplotlib.pyplot as plt

app = Flask(__name__)

# удалять фигню в тексте
def clean_line(line):
    regTag = re.compile('<.*?>', flags=re.DOTALL)
    regLink = re.compile('https?:\/\/(?:www\.|(?!www))[^\s\.]+\.[^\s]{2,}|www\.[^\s]+\.[^\s]{2,}', flags=re.DOTALL)
    regName = re.compile('\[id[0-9]+?|.*?\], ', flags=re.DOTALL)
    regHashtag = re.compile('#.? ', flags=re.DOTALL)
    regBegin = re.compile('^-')
    line = regTag.sub('', line)
    line = regLink.sub('', line)
    line = regName.sub('', line)
    line = regHashtag.sub('', line)
    line = regBegin.sub('', line)
    line = html.unescape(line)
    return line

# выяснять id группы
def group_id(domain):
    params = {'group_id': domain, 'version': '5.62', 'fields': 'members_count, screen_name'}
    response = requests.get('https://api.vk.com/method/groups.getById', params=params)
    group_json = response.json()['response'][0]
    return group_json['gid']

# получать посты
def get_posts(parameters, offset, post_ids, length_dict):
    parameters['count'] = '100'
    parameters['offset'] = offset*100
    response = requests.get('https://api.vk.com/method/wall.get', params=parameters)
    if response:
        for i in range(1, len(response.json()['response'])):
            post = response.json()['response'][i]
            # очищаем текст поста от всякого
            text = clean_line(post['text'])
            # собираем такую строчку в posts, чтобы потом иметь id поста
            post_ids.add(str(post['id']))
            # posts_dict — это словарь типа {"id запостившего": длина поста}
            if length_dict[str(post['from_id'])]:
                length_dict[str(post['from_id'])] = max(length_dict[str(post['from_id'])], len(text))
            else:
                length_dict[str(post['from_id'])] = len(text)
    return posts, length_dict


def posts(group_domain):
    parameters = {'domain': group_domain,
                  'version': '5.65',
                  'access_token': '6b3692fe7ffcf891a0300721a80357faa87c72f7a8db5e91974512896ff0ffc7242b9688edaa794e33e1a'
                  }
    # этот response только чтобы посмотреть на итоговое количество
    response = requests.get('https://api.vk.com/method/wall.get', params=parameters)
    # post_texts -- всякая инфа про посты, dict_posts_length -- словарь типа {"id запостившего": длина поста}
    post_ids = set()
    length_dict = {}
    if response and response.json()['response'][0] > 100:
        if response.json()['response'][0] > 100:
            # если постов больше 100, то цикл
            for i in range(response.json()['response'][0] % 100 + 1):
                post_ids, length_dict = get_posts(parameters, i * 100, post_ids, length_dict)
            # если меньше, то смещение = 0
            else:
                post_ids, length_dict = get_posts(parameters, 0, post_ids, length_dict)
    return post_ids, length_dict


def get_comments(params, offset, comments_dict, interaction_dict, from_id):
    params['offset'] = offset
    link = 'https://api.vk.com/method/wall.getComments'
    response = requests.get(link, params=params)
    if response:
        for i in range(1, len(response.json()['response'])):
            comment = response.json()['response'][i]
            interaction_dict[from_id].append(str(comment['from_id']))
            comments['from_id'] = len(comment['text'])
    return comments_dict, interaction_dict


def comments(post_ids, group_id, length_dict):
    interaction_dict = {post: [] for post in post_ids}
    owner_id = '-' + str(group_id)
    parameters = {'version': '5.62',
                  'owner_id': owner_id,
                  'post_id': '',
                  'count': '100',
                  'access_token': '6b3692fe7ffcf891a0300721a80357faa87c72f7a8db5e91974512896ff0ffc7242b9688edaa794e33e1a'
                  }
    for post in post_ids:
        parameters['post_id'] = post
        response = requests.get('https://api.vk.com/method/wall.getComments', params=parameters)
        if response and response.json()['response'][0] > 100:
            if response.json()['response'][0] > 100:
                # если постов больше 100, то цикл
                for i in range(response.json()['response'][0] % 100 + 1):
                    length_dict, interaction_dict = get_comments(parameters, i * 100, length_dict, interaction_dict, post)
                # если меньше, то смещение = 0
                else:
                    length_dict, interaction_dict = get_comments(parameters, 0, length_dict, interaction_dict, post)
    return length_dict, interaction_dict


def do_graph_data(group_link):
    group_domain = str(group_link.split('/')[1])
    # данные
    id = group_id(group_domain)
    post_ids, length_dict = posts(group_domain)
    length_dict, interaction_dict = comments(post_ids, id, length_dict)
    # граф
    graph = nx.Graph()
    for id in length_dict:
        graph.add_node(id, weight=length_dict[id])
    pos = nx.spring_layout(graph)
    nx.draw_networkx_nodes(graph, pos)
    for first_id in interaction_dict:
        for second_id in interaction_dict[first_id]:
            graph.add_edge(first_id, second_id)
    nx.draw_networkx_edges(graph, pos)
    plt.axis('off')
    plt.savefig('./static/graph.png', format='PNG')


@app.route('/results')
def results():
    if request.args:
        group_link = request.args.get('address')
        do_graph_data(group_link)
    return render_template('results.html')

@app.route('/')
def index():
    if request.args:
        group_link = request.args.get('address')
    return render_template('index.html')


if __name__ == '__main__':
    app.run()