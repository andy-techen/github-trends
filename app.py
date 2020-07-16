import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from github_crawler import get_keywords, GitHub
import numpy as np

THEME = dbc.themes.SIMPLEX
LOGO = 'https://3u26hb1g25wn1xwo8g186fnd-wpengine.netdna-ssl.com/files/2019/06/moz-logo-white.png'

app = dash.Dash(__name__, external_stylesheets=[THEME])
server = app.server

header = dbc.Navbar(
    [
        dbc.Col(
            dbc.NavbarBrand(
                "Github Trends",
                href="https://github.com/Dershan219/github-trends"),
                style={'font-weight':'bold'},
            width=1.5
        ),
        dbc.Col(
            dbc.Input(
                id='keyword', value='Mozilla VPN',
                type='text', placeholder="Enter Keywords (sep by '/')",
                style={'height':'36px', 'margin-top':'0px'}
            ),
            width=10
        ),
        dbc.Col(
            dbc.Button(
                "Search", id="keyword-search", n_clicks=0, color="secondary",
                style={'height':'36px', 'margin-top':'0px', 'padding':'0rem 1rem'}
                ),
            width=0.5
        ),
        html.Div(children=[""],id='input-temp', style={'display': 'none'})
    ],
    color="dark",
    dark=True,
)

filters = dbc.Row(
    [
        dbc.Col(
            [
                html.Div(children=[""],id='filters-temp', style={'display': 'none'}),
                html.P("Number of Repositories", style={'textAlign':'center'}),
                dbc.Input(id='n-repos', type="number", value=10, min=10, max=30, step=5)
            ],
            width=2
        )
    ],
    justify='center'
)

table_header = [
    html.Thead(
        html.Tr(
            [
                html.Th("Name"),
                html.Th("Url"),
                html.Th("Description"),
                html.Th("Forks"),
                html.Th("Stars")
            ]
        )
    )
]

tab1 = dbc.Row(
    [
        dbc.Spinner(html.Div(id='repo-table'))
    ],
    justify='center'
) 

tab2 = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.FormGroup(
                            [
                                html.Br(),
                                dbc.Label("Number of Keywords", html_for='n-words'),
                                dcc.Slider(
                                    id='n-words',
                                    min=10, max=50, step=5, value=30,
                                    marks={
                                        10:'10',
                                        20:'20',
                                        30:'30',
                                        40:'40',
                                        50:'50'
                                    })
                            ]
                        )
                    ],
                    width=6
                )
            ],
            justify='center'
        ),    
        dbc.Row(dbc.Spinner(dcc.Graph(id='keyword-cloud')), justify='center')
    ]
)

body = dbc.Container(
    [
        html.Br(),
        dbc.Tabs(
            [
                dbc.Tab(tab1, label="Top Repos", tab_style={'margin-left':'auto'}),
                dbc.Tab(tab2, label="Top Keywords")
            ]
        )
    ]
)

@app.callback(
    [Output('input-temp', 'children'),
    Output('filters-temp', 'children')],
    [Input('keyword-search', 'n_clicks')],
    [State('keyword', 'value'),
    State('n-repos', 'value')]
)
def update_temp(click, keyword, n_repos):
    return keyword, n_repos

def get_repos(keywords, n_repos=20):
    github = GitHub(keywords, n_repos=n_repos)
    return github.get_github_keywords()

@app.callback(
    [Output('repo-table', 'children')],
    [Input('input-temp', 'children'),
    Input('filters-temp', 'children')]
)
def update_repo_table(keywords, n_repos):
    keywords = keywords.split('/')
    github_repos = get_repos(keywords, n_repos=n_repos)[0]

    table_body = []
    for row in github_repos.itertuples():
        table_body.append(
            html.Tr(
                [
                    html.Td(row.name),
                    html.Td(html.A(row.url, href=row.url, target='_blank', style={'color':'#1D5286'})),
                    html.Td(row.description),
                    html.Td(row.forks),
                    html.Td(row.stars)
                ]
            )
        )
    try:
        return [dbc.Table(table_header + [html.Tbody(table_body)], hover=True)]
    # try:
    #     return [dbc.Table.from_dataframe(github_repos.drop(['readme'], axis=1), hover=True)]
    except Exception as e:
        print(e)
        return [dbc.Alert("Renew Gihub Token!", color="danger")]

def plot_wordcloud(df, n_words):

    words = df.keys().tolist()
    frequency = np.interp(df.values, (df.values.min(), df.values.max()), (10,100)).tolist()
    palette = ['#1D5286', '#4A89BF', '#8DB8E2', '#81888F', '#BEC2C5']
    colors = np.random.choice(palette, size=n_words)
    x = np.random.choice(n_words, size=n_words) + 0.5 * np.random.rand(n_words)
    y = np.random.choice(n_words, size=n_words) + 0.5 * np.random.rand(n_words)
    
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode='text',
            text=words,
            hoverinfo='text',
            hovertext=['{0}: {1}'.format(w, int(f)) for w, f in zip(words, frequency)],
            textfont={'size': frequency, 'color': colors}
        )
    )
    figure.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=450, width=750,
        margin=go.layout.Margin(t=10)
    )

    return figure

@app.callback(
    [Output('keyword-cloud', 'figure')],
    [Input('input-temp', 'children'),
    Input('filters-temp', 'children'),
    Input('n-words', 'value')]
)
def update_keyword_cloud(keywords, n_repos, n_words):
    keywords = keywords.split('/')
    github_keywords = get_repos(keywords, n_repos=n_repos)[1]

    figure = plot_wordcloud(github_keywords, n_words)
    
    return [figure]

app.layout = html.Div(
    [
        header,
        html.Br(),
        filters,
        body
    ]
)

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
