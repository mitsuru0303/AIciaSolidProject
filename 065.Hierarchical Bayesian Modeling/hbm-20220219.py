# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.13.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# !pip install pymc3

# +
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from pandas_profiling import ProfileReport
import pymc3 as pm
import re
from sklearn.linear_model import LinearRegression

# %matplotlib inline
# -

# # import data - データの読み込み

# +
df_videos = pd.read_csv(os.path.join('..', 'data', 'AIcia_videos_20220219.csv'))
df_videos['動画公開時刻'] = pd.to_datetime(df_videos['動画公開時刻'])
# df_videos['動画時間_s'] = pd.to_timedelta(df_videos['動画時間']).apply(lambda x: x.seconds)
df_videos = df_videos.sort_values('動画公開時刻')

# df_videos = df_videos.drop(['動画時間'], axis=1)

df_videos = df_videos.dropna()
df_videos = df_videos[df_videos['動画のタイトル'].apply(lambda x: len(re.compile(r'\#\d{3}').findall(x))>0)]
df_videos = df_videos[~df_videos['動画のタイトル'].apply(lambda x: 'LIVE' in x)]
df_videos = df_videos[~df_videos['動画のタイトル'].apply(lambda x: 'ライブ' in x)]
df_videos = df_videos[~df_videos['動画のタイトル'].apply(lambda x: '生放送' in x)]
df_videos = df_videos[~df_videos['動画のタイトル'].apply(lambda x: '週末微分幾何' in x)]

lst_live_titles = [
    '【VRアカデミア対談】 いたりんっ × アイシア 【第一弾だよ！】#VRアカデミア #004',
]
df_videos = df_videos[df_videos['動画のタイトル'].apply(lambda x: x not in lst_live_titles)]

df_videos = df_videos.reset_index(drop=True)

df_videos.head()
# -

df_videos['動画のタイトル'].values

profile = ProfileReport(df_videos, title='Pandas Profiling Report', html={'style':{'full_width':True}})

profile

# # Hierarchical Bayesian Modeling

n_videos = len(df_videos)

# +
# define model and sample

with pm.Model() as model:
    # prior to parameters
    alpha_plus = pm.Normal('alpha_plus', mu=-3, sd=2)
    beta_plus = pm.TruncatedNormal('beta_plus', mu=0, sd=1, lower=0)
    alpha_minus = pm.Normal('alpha_minus', mu=-3, sd=2)
    beta_minus = pm.TruncatedNormal('beta_minus', mu=0, sd=1, upper=0)
    
    # prior to fun
    fun = pm.Normal('fun', mu=0, sd=1, shape=n_videos)
    
    # play
    play = df_videos['視聴回数']
    
    # +1 and -1
    lambda_plus = pm.math.exp((alpha_plus + beta_plus * fun)) * play
    like = pm.Poisson('like', mu=lambda_plus, observed=df_videos['高評価数'])
    
    lambda_minus = pm.math.exp((alpha_minus + beta_minus * fun)) * play
    dislike = pm.Poisson('dislike', mu=lambda_minus, observed=df_videos['低評価数'])
    
    trace = pm.sample(1500, tune=3000, chains=5, random_seed=57)
# -

pm.traceplot(trace)

# +
df_trace = pm.summary(trace)

df_trace
# -

model_map = pm.find_MAP(model=model)
model_map

df_trace.loc['fun[0]':'beta_plus', ['mean']].sort_values('mean', ascending=False)

# +
df_videos['fun'] = model_map['fun']

df_videos = df_videos.sort_values(by='fun', ascending=False)

print('top 5 fun videos!')
display(df_videos.head(5))

print('worst 5 fun videos...')
display(df_videos.tail(5))
# -

# # fun vs comment

with pm.Model() as model_with_comment:
    # prior to parameters
    alpha_plus = pm.Normal('alpha_plus', mu=-3, sd=2)
    beta_plus = pm.TruncatedNormal('beta_plus', mu=0, sd=1, lower=0)
    alpha_minus = pm.Normal('alpha_minus', mu=-3, sd=2)
    beta_minus = pm.TruncatedNormal('beta_minus', mu=0, sd=1, upper=0)
    alpha_comment = pm.Normal('alpha_comment', mu=-3, sd=2)
    beta_comment = pm.TruncatedNormal('beta_comment', mu=0, sd=1, lower=0)
    
    # prior to fun
    fun = pm.Normal('fun', mu=0, sd=1, shape=n_videos)
    
    # prior to comment
    latent_comment = pm.Normal('latent_comment', mu=0, sd=1, shape=n_videos)
    
    # play
    play = df_videos['視聴回数']
    
    # +1, -1, comment
    lambda_plus = pm.math.exp((alpha_plus + beta_plus * fun)) * play
    like = pm.Poisson('like', mu=lambda_plus, observed=df_videos['高評価数'])
    
    lambda_minus = pm.math.exp((alpha_minus + beta_minus * fun)) * play
    dislike = pm.Poisson('dislike', mu=lambda_minus, observed=df_videos['低評価数'])
    
    lambda_comment = pm.math.exp((alpha_comment + beta_comment * latent_comment)) * play
    comment = pm.Poisson('comment', mu=lambda_comment, observed=df_videos['コメント'])
    
    trace = pm.sample(1500, tune=1000, chains=5, random_seed=57)

pm.traceplot(trace)

# +
df_trace = pm.summary(trace)

df_trace
# -

df_latent = df_trace.loc['fun[0]':'latent_comment[62]', ['mean']].reset_index()
df_latent['variable'] = df_latent['index'].apply(lambda x: x.split('[')[0])
df_latent['index'] = df_latent['index'].apply(lambda x: x.split('[')[1].split(']')[0])
df_latent = df_latent.set_index(['index', 'variable']).unstack()

df_latent.describe()

# +
# correlation between "fun" and "tendency to comment"

df_latent.corr()
# -
# # Additional survey on dependency of #views on #likes/#views 


# +
fig, ax = plt.subplots()

ax.scatter(df_videos['視聴回数'], df_videos['高評価数'])
ax.set_xlabel('views', fontsize='xx-large')
ax.set_ylabel('likes', fontsize='xx-large')


# +
fig, ax = plt.subplots()

ax.scatter(np.log(df_videos['視聴回数']), np.log(df_videos['高評価数']))
ax.set_xlabel('ln_views', fontsize='xx-large')
ax.set_ylabel('ln_likes', fontsize='xx-large')

# +
fig, ax = plt.subplots()

ax.scatter(np.log(np.log(df_videos['視聴回数'])), np.log(np.log(df_videos['高評価数'])))
ax.set_xlabel('ln_ln_views', fontsize='xx-large')
ax.set_ylabel('ln_ln_likes', fontsize='xx-large')

# +
fig, ax = plt.subplots(figsize=(10, 5))

data_x = df_videos[['視聴回数']]
data_y = df_videos['高評価数']/df_videos['視聴回数']

x_linsp = np.linspace(0, data_x.max()+1000, 1000)

lm = LinearRegression()
lm.fit(data_x, data_y)

ax.plot(x_linsp, lm.predict(x_linsp), label='regression line', color='orange')
ax.scatter(data_x, data_y, label='raw data')
ax.set_xlabel('views', fontsize='xx-large')
ax.set_ylabel('likes / views', fontsize='xx-large')
ax.legend(fontsize='x-large')
# -

# やっぱり、再生数が大きいと、高評価割合が下がるような気がする（気がする）
#
# この補正も入れて面白さ度合いを出してみよう！

# # Hierarchical Bayesian Modeling with correction on the above effect

n_videos = len(df_videos)

# +
# define model and sample

with pm.Model() as model:
    # prior to parameters
    alpha_plus = pm.Normal('alpha_plus', mu=-3, sd=2)
    beta_plus = pm.TruncatedNormal('beta_plus', mu=0, sd=1, lower=0)
    gamma_plus = pm.TruncatedNormal('gamma_plus', mu=0, sd=1, upper=0)
    alpha_minus = pm.Normal('alpha_minus', mu=-3, sd=2)
    beta_minus = pm.TruncatedNormal('beta_minus', mu=0, sd=1, upper=0)
    
    # prior to fun
    fun = pm.Normal('fun', mu=0, sd=1, shape=n_videos)
    
    # play
    play = df_videos['視聴回数']
    
    # +1 and -1
    lambda_plus = pm.math.exp(alpha_plus + beta_plus * fun + gamma_plus * play / 100000000) * play
    like = pm.Poisson('like', mu=lambda_plus, observed=df_videos['高評価数'])
    
    lambda_minus = pm.math.exp(alpha_minus + beta_minus * fun) * play
    dislike = pm.Poisson('dislike', mu=lambda_minus, observed=df_videos['低評価数'])
    
    trace = pm.sample(1500, tune=3000, chains=5, random_seed=57)
# -

pm.traceplot(trace)

# +
df_trace = pm.summary(trace)

df_trace
# -

model_map = pm.find_MAP(model=model)
model_map

# +
df_videos['fun'] = model_map['fun']

df_videos = df_videos.sort_values(by='fun', ascending=False)

print('top 5 fun videos!')
display(df_videos.head(5))

print('worst 5 fun videos...')
display(df_videos.tail(5))
# -

# 結果は変わらず。残念。


