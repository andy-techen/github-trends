# -*- coding: utf-8 -*- 
#%%
# basics
import json
import numpy as np
import pandas as pd
import os
from datetime import datetime
# apis
import requests
from tweepy import API, OAuthHandler
# text
import string
import re
import pybase64
# import nltk
# nltk.download('stopwords')
# nltk.download('punkt')
from nltk import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfTransformer, CountVectorizer
from secrets import *

# settings-------------------------------------------------------------------
# base variables
BASE_API = "https://api.github.com/search/repositories?q="
token_header = {'Authorization': 'token ' + g_access_token}

# keyword extraction preps
stop = stopwords.words('english') + list(string.punctuation)
update_stop = ["rt", "com", "could"]
stop.extend(update_stop)
cv = CountVectorizer(ngram_range=(1,2))
transformer = TfidfTransformer()

# twitter auth
auth = OAuthHandler(t_consumer_key, t_consumer_secret)
auth.set_access_token(t_access_token, t_access_secret)
api = API(auth)

# utility functions----------------------------------------------------------
# generate top keywords & tfidf scores
def get_keywords(df):
    # remove stopwords
    content_ls = []
    for c in df:
        text_ls = word_tokenize(c)
        text_ls = [txt.lower() for txt in text_ls if txt.lower() not in stop]
        content_ls.append(' '.join(text_ls))
    
    # feature extraction
    content_vector = cv.fit_transform(content_ls)
    values = transformer.fit_transform(content_vector).todense()
    features = cv.get_feature_names()
    return pd.DataFrame(values, columns=features)

# obtain tweets
def get_twitter_query(keywords):
    keywords_str = '"' + '" OR "'.join(keywords) + '"'
    results = api.search(keywords_str, count=100, tweet_mode='extended', lang='en')
    results_df = pd.json_normalize([r._json for r in results])
    print("Fetched Tweets")
    return results_df['full_text']

# obtain keywords from tweets
def get_twitter_keywords(keywords, n_words=50):
    tweets_df = get_twitter_query(keywords)
    keywords_df = get_keywords(tweets_df)
    return tweets_df, keywords_df.agg('sum').nlargest(n_words)

# obtain github repos
def get_github_query(keywords, min_stars=10, min_forks=10, n_repos=50):
    # construct query
    keywords_str = '"' + '"+OR+"'.join(keywords) + '"'
    filters_str = "&stars:>{}&forks:>{}&sort=stars&per_page={}".format(min_stars, min_forks, n_repos)
    query = BASE_API + keywords_str + filters_str

    # collect metadata
    q = requests.get(query, headers=token_header)
    repos = json.loads(q.content)['items']
    repos_df = pd.DataFrame(repos)
    repos_df = repos_df.loc[:, ['name', 'html_url', 'description', 'forks', 'stargazers_count', "url"]]

    # collect readme files
    readme_ls = []
    ct = 1
    for i in repos_df['url']:
        print(f'Fetching Repo #{ct}: {i}')
        readme_url = i + "/contents/README.md?ref=master"
        r = requests.get(readme_url, headers=token_header)
        if r.status_code == 200:
            readme = json.loads(r.content)['content']
            readme_text = pybase64.b64decode(readme).decode('utf-8')
            readme_text = re.sub(r"[^\w\s'.:/]",'',readme_text).replace('\n',' ')
            readme_ls.append(readme_text)
        elif r.status_code == 401:
            print("Renew Github Token!")
        else:
            readme_ls.append(np.nan)
        ct += 1
    repos_df['readme'] = readme_ls

    repos_df.drop(['url'], axis=1, inplace=True)
    repos_df.columns = ['name', 'url', 'description', 'forks', 'stars', 'readme']
    print("Fetched Repos")
    return repos_df

# obtain keywords from repos
def get_github_keywords(keywords, n_words=50, min_stars=10, min_forks=10, n_repos=50):
    repos_df = get_github_query(keywords, min_stars, min_forks, n_repos)
    text_cols = ['name', 'description', 'readme']
    repos_df['content'] = repos_df[text_cols].apply(lambda row: ' '.join(row.values.astype(str)), axis=1)
    repos_df.dropna(subset=['content'], inplace=True)
    keywords_df = get_keywords(repos_df['content'])
    return repos_df.drop(['content'], axis=1), keywords_df.agg('sum').nlargest(n_words)


if __name__ == '__main__':
    base_keywords = ["vpn", "anonymous browsing", "online tracking", "online surveillance"]
    keywords = input("Keywords (sep with '/'): ") or "/".join(base_keywords)
    n_repos = int(input("Number of Repos: ") or 50)
    keywords = keywords.split('/')
    twitter_keywords = get_twitter_keywords(keywords=keywords)[1]
    github_repos, github_keywords = get_github_keywords(keywords=keywords, n_repos=n_repos)
    date = datetime.now().strftime('%Y_%m_%d')

    with pd.ExcelWriter(f'{date}_test.xlsx') as writer:
        twitter_keywords.to_excel(writer, 'twitter_keywords', header=['sum_tfidf'], index_label='term')
        github_repos.to_excel(writer, 'github_repos', index=False, encoding='utf-8')
        github_keywords.to_excel(writer, 'github_keywords', header=['sum_tfidf'], index_label='term', encoding='utf-8')