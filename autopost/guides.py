"""How-to posts with picture cards, one a day from the official account (setup_guides_v1).
Each guide teaches one XpertCreation module step by step. Add new ones to the end of GUIDES."""
import os
import secrets
import shutil

from django.conf import settings

from .models import AutoPost
from . import posting

IMG_DIR = os.path.join(os.path.dirname(__file__), "guide_images")
GUIDES = [
 {
  "key": "steps-1-walk",
  "module": "Step counter",
  "text": "🚶 How to use the Xpert Step Counter – Part 1: your first walk\n\n1) Open xpertcreation.com/steps or the Xpert app → Step counter.\n2) Tap Start. Allow location (for the map) and motion (for steps) when your phone asks.\n3) Put the phone in your pocket and walk. Steps, distance and your route appear live, and the map turns with you.\n4) Tap Stop when you finish. Your next walk starts again from zero, and today's total keeps adding up.\n\nIt's free and works on any phone. A 20-minute walk a day is one of the best things you can do for your health.\n\nTry it now: https://xpertcreation.com/steps\n\n#XpertCreation #StepCounter #Walking #HealthyLiving #HowTo"
 },
 {
  "key": "steps-2-run",
  "module": "Step counter",
  "text": "🏃 How to use the Xpert Step Counter – Part 2: going for a run\n\n1) Open Step counter and tap Start just before you set off.\n2) The map follows you with your direction arrow and draws your route as you go. Tap the compass for north-up, or the target to follow yourself again.\n3) Watch your distance, steps and time while you run.\n4) Tap Stop at the end – the run is added to today's total and your hour-by-hour chart.\n\nTip: start slow, run for 1 minute and walk for 2, and repeat. In a few weeks you can run much longer.\n\nhttps://xpertcreation.com/steps\n\n#XpertCreation #Running #StepCounter #Fitness #HowTo"
 },
 {
  "key": "steps-3-goal",
  "module": "Step counter",
  "text": "🎯 How to use the Xpert Step Counter – Part 3: goals and streaks\n\n1) Tap Set goal and pick a daily target – start with 6,000 if 10,000 feels like a lot.\n2) The ring fills up as you walk. Reach your goal on several days in a row and your streak grows.\n3) Open Daily totals to see every day, and the hour-by-hour chart to see when you are most active.\n\nSmall daily goals beat one big walk a week. What's your streak today? Tell us in the comments.\n\nhttps://xpertcreation.com/steps\n\n#XpertCreation #StepChallenge #DailyGoal #HealthyHabits #HowTo"
 },
 {
  "key": "steps-4-share",
  "module": "Step counter",
  "text": "🤝 How to use the Xpert Step Counter – Part 4: share and motivate\n\n1) When you reach your goal, the step counter offers to share it.\n2) Tap Post on XpertConnect to share with your network, or send it to WhatsApp, Facebook or X.\n3) Invite family and friends – walking together is easier, and a friendly challenge keeps everyone going.\n\nShare this post with someone who should walk more today 🙂\n\nhttps://xpertcreation.com/steps\n\n#XpertCreation #WalkTogether #StepCounter #Motivation #HowTo"
 },
 {
  "key": "meetups",
  "module": "Meetups",
  "text": "👥 How to use Meetups on XpertCreation\n\n1) Open xpertcreation.com/meetups (also in the menu). Search by city, or tap a topic: tech, business, careers, sports, languages and more.\n2) Join a group. You get a notification every time it schedules a meetup.\n3) Open a meetup and tap I'm going. If the seats are full you join the waitlist and move up by yourself when someone cancels.\n4) We remind you a day before. Online meetups show the joining link once you are going.\n\nWant to start your own group? Verify your ID first, then tap + Start a group.\n\nhttps://xpertcreation.com/meetups\n\n#XpertCreation #Meetups #Networking #Community #HowTo"
 },
 {
  "key": "academy",
  "module": "XpertAcademy",
  "text": "🎓 How to learn on XpertAcademy – free, with a certificate\n\n1) Open xpertcreation.com/academy and choose a course: Python, JavaScript, Django, React, Word, Excel, IELTS, languages, Blockchain basics and more.\n2) Do one short lesson a day. Sign in to save your progress.\n3) At the end, take the quiz. Pass it and you get a certificate with your name.\n4) Anyone can check your certificate is real with Check a certificate at the bottom of the page.\n\nTag a friend who wants to learn something new this month.\n\nhttps://xpertcreation.com/academy/\n\n#XpertCreation #XpertAcademy #LearnOnline #FreeCourses #HowTo"
 },
 {
  "key": "freelance",
  "module": "Freelance",
  "text": "💼 How to use Freelance on XpertCreation\n\nBuying:\n1) Open xpertcreation.com/market and search for what you need – design, writing, websites, typing and more.\n2) Order a ready-made gig, or post a project and choose the best bid.\n3) Chat with the seller and get the files in your order.\n\nSelling:\n1) Verify your ID (only verified members can sell).\n2) Add your gigs with clear prices and delivery times.\n3) Deliver on time to get good reviews.\n\nhttps://xpertcreation.com/market\n\n#XpertCreation #Freelance #WorkFromHome #Pakistan #HowTo"
 },
 {
  "key": "store",
  "module": "Store",
  "text": "🛍 How to shop on the XpertCreation Store\n\n1) Open xpertcreation.com/store and search or browse categories.\n2) Add products to your cart – items from different sellers go in one cart.\n3) Check out and pay cash on delivery or online.\n4) After delivery, leave a review to help other buyers.\n\nHave a business? Sellers apply with a complete profile and an approved ID check, then list their products.\n\nhttps://xpertcreation.com/store\n\n#XpertCreation #OnlineShopping #Store #Pakistan #HowTo"
 },
 {
  "key": "rides",
  "module": "Ladies rides",
  "text": "🚗 How to book a Ladies ride on XpertCreation\n\n1) Open xpertcreation.com/rides.\n2) Set your pickup and drop-off on the map – you see the road route.\n3) Choose a car, rickshaw or bike and request the ride. A nearby woman driver accepts and you see her coming on the live map.\n4) Pay the driver in cash at the end.\n\nWomen who want to drive can apply in Rides: ID check plus licence and vehicle papers, approved by our team.\n\nhttps://xpertcreation.com/rides\n\n#XpertCreation #LadiesRides #SafeTravel #WomenDrivers #HowTo"
 },
 {
  "key": "connect",
  "module": "XpertConnect",
  "text": "🤝 How to use XpertConnect\n\n1) Open xpertcreation.com/feed and complete your profile – photo, headline, skills and experience.\n2) Send connection requests. Chat opens once a request is accepted.\n3) Post updates, photos and polls, and wish your connections on birthdays and work anniversaries.\n4) Looking for work or hiring? Add the #OpenToWork or #Hiring frame to your photo.\n\nShare this with a friend who should be on XpertConnect.\n\nhttps://xpertcreation.com/feed\n\n#XpertCreation #XpertConnect #Networking #Careers #HowTo"
 },
 {
  "key": "verify",
  "module": "Get verified",
  "text": "🛡 How to get ID verified on XpertCreation\n\n1) Open xpertcreation.com/get-verified.\n2) Upload clear photos of your ID and an address proof, and add your WhatsApp number.\n3) Our team reviews it, usually within a day. You get a notification when it is approved.\n\nVerified members can sell on Freelance and the Store, organise Meetups and drive in Ladies rides – and people trust a verified profile more.\n\nhttps://xpertcreation.com/get-verified\n\n#XpertCreation #Verified #TrustAndSafety #HowTo"
 },
 {
  "key": "chatrooms",
  "module": "Chat rooms",
  "text": "💬 How to use Chat rooms on XpertCreation\n\n1) Open xpertcreation.com/chat-rooms – you can join as a guest.\n2) Pick a room: #pakistan, #shairi for Urdu poetry, #coding and more – or register your own.\n3) Sign in with your XpertCreation account to keep your nickname.\n4) Prefer a classic IRC app like mIRC? Connect to irc.xpertcreation.com.\n\nBe kind, and report anyone who breaks the rules.\n\nhttps://xpertcreation.com/chat-rooms\n\n#XpertCreation #ChatRooms #IRC #Community #HowTo"
 }
]


def next_guide():
    done = set(AutoPost.objects.filter(kind="guide").values_list("key", flat=True))
    return next((g for g in GUIDES if g["key"] not in done), None)


def post_guide(key=None):
    g = next((x for x in GUIDES if x["key"] == key), None) if key else next_guide()
    if not g:
        return None
    images = []
    src = os.path.join(IMG_DIR, g["key"] + ".webp")
    if os.path.exists(src):
        u = posting.official()
        rel = "feed/%d/guide-%s-%s.webp" % (u.id, g["key"], secrets.token_hex(6))
        full = os.path.join(str(settings.MEDIA_ROOT), rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        shutil.copyfile(src, full)
        images = [rel]
    return posting._publish("guide", g["key"], g["text"], images=images)
