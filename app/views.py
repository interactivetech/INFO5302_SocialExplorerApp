from facebook import get_user_from_cookie, GraphAPI
from flask import g, render_template, redirect, request, session, url_for

from app import app, db
from models import User

from TwitterSearch import *
from os import path
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Facebook app details
FB_APP_ID = ''
FB_APP_NAME = ''
FB_APP_SECRET = ''

import os

import requests
import json
from pprint import pprint

def getPlaces(posts):
    print "In Places!"
    placeslist = []
    zipcodes = []
    for i in posts['data']:
        placeslist.append(i['place']['name'])
        if 'zip' in i['place']['location']:
            zipcodes.append(i['place']['location']['zip'])
    zipcodes = zipcodes
    placeslist = placeslist
    print "Finished Places!"
    return placeslist,zipcodes

def retrievetweets(places):
    print "In Tweets!"
    tso = TwitterSearchOrder() # create a TwitterSearchOrder object
    # it's about time to create a TwitterSearch object with our secret tokens
    ts = TwitterSearch(
        consumer_secret = '',
        access_token = '',
        access_token_secret = '',
        consumer_key = ''
     )
    tso.set_language('en') # we want to see German tweets only
    tso.set_include_entities(False) # and don't give us all those entity information
    names=[]
    for i in places:
        #save tweets into files
        filename =  os.getcwd()+'/app/static/places_'+ i +'.txt'
        tweetsfile = open(filename, 'w')
        tso.set_keywords([i]) 
        for tweet in ts.search_tweets_iterable(tso):
            tweetsfile.write(tweet['text'].encode('utf-8'))
        tweetsfile.close()
        
        #create word cloud
        text = open(filename).read()
        #make sure it's not an empty file
        if os.stat(filename).st_size != 0:
            # Generate a word cloud image
            wordcloud = WordCloud(max_font_size=40).generate(text)
            plt.figure()
            plt.imshow(wordcloud)
            name = str(i)
            name = name.replace(' ','_')
            names.append(name)
            plt.axis("off")
            plt.title(str(i)) 
            plt.savefig(os.getcwd()+"/app/static/"+name+".png",dpi=300)  
        print "In Tweets!"
    return names

@app.route('/')
def index():
    # If a user was set in the get_current_user function before the request,
    # the user is logged in.
    if g.user:
        return render_template('index.html', app_id=FB_APP_ID,
                               app_name=FB_APP_NAME, user=g.user)
    # Otherwise, a user is not logged in.
    return render_template('login.html', app_id=FB_APP_ID, name=FB_APP_NAME)

@app.route('/createSociogram',methods=['GET', 'POST'])
def sociogram():
    [zipcodes,event,places]=run_program()
    return render_template('res.html', app_id=FB_APP_ID,
                               app_name=FB_APP_NAME, events=[zipcodes,event,places])


@app.route('/logout')
def logout():
    """Log out the user from the application.

    Log out the user from the application by removing them from the
    session.  Note: this does not log the user out of Facebook - this is done
    by the JavaScript SDK.
    """
    session.pop('user', None)
    return redirect(url_for('index'))


@app.before_request
def get_current_user():
    """Set g.user to the currently logged in user.

    Called before each request, get_current_user sets the global g.user
    variable to the currently logged in user.  A currently logged in user is
    determined by seeing if it exists in Flask's session dictionary.

    If it is the first time the user is logging into this application it will
    create the user and insert it into the database.  If the user is not logged
    in, None will be set to g.user.
    """

    # Set the user in the session dictionary as a global g.user and bail out
    # of this function early.
    if session.get('user'):
        print "Bail!"
        g.user = session.get('user')
        return

    # Attempt to get the short term access token for the current user.
    result = get_user_from_cookie(cookies=request.cookies, app_id=FB_APP_ID,
                                  app_secret=FB_APP_SECRET)

    # If there is no result, we assume the user is not logged in.
    if result:
        # Check to see if this user is already in our database.
        user = User.query.filter(User.id == result['uid']).first()

        if not user:
            print "One"
            # Not an existing user so get info
            graph = GraphAPI(result['access_token'])
            profile = graph.get_object('me')
            if 'link' not in profile:
                profile['link'] = ""
            # print profile['education']
            

            # Create the user and insert it into the database
            user = User(id=str(profile['id']), name=profile['name'],
                        profile_url=profile['link'],
                        access_token=result['access_token'])
            db.session.add(user)

        elif user.access_token != result['access_token']:
            # print "Two"
            # print result['access_token']

            # If an existing user, update the access token
            user.access_token = result['access_token']

            graph = GraphAPI(result['access_token'])
            profile = graph.get_object('me')
            # res = graph.get_connections(profile['id'],'hometown')
            if 'link' not in profile:
                profile['link'] = ""
            # print res
        # Add the user to the current session
        session['user'] = dict(name=user.name, profile_url=user.profile_url,
                               id=user.id, access_token=user.access_token)
       

        # profile = graph.get_object('me')
        # posts = graph.get_connections('me', 'tagged_places')
        # # for post in posts['data']:
        # #     print  post['place']['name'].encode('ascii',errors="ignore"), post['place']['location']

        # places,zipcodes = getPlaces(posts)
        # retrievetweets(places[:20])


    # Commit changes to the database and set the user as a global g.user
    db.session.commit()
    g.user = session.get('user', None)


#retrieve top events happening at tagged places 
def getEvent(zipcodes):
    event = []
    for i in zipcodes:
        query = "https://www.eventbriteapi.com/v3/events/search?location.address=" + str(i)
        response = requests.get(query,
            headers = {
                "Authorization": "",},
            verify = True,  # Verify SSL certificate
        )
        event.append(str("Event at " + i + ": " + response.json()['events'][0]['name']['text']))
    event = event
    return event

def run_program():
    graph = GraphAPI("")
    profile = graph.get_object('me')
    posts = graph.get_connections('me', 'tagged_places')
    # for post in posts['data']:
    #     print  post['place']['name'].encode('ascii',errors="ignore"), post['place']['location']

    places,zipcodes = getPlaces(posts)
    names = retrievetweets(places[:20])
    event = getEvent(zipcodes)
    print names
    return [zipcodes,event,names]

