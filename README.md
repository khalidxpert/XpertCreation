# XpertCreation

A small platform of free tools, built for Pakistan and open to anyone. One
account works across all of them.

**Live at [xpertcreation.com](https://xpertcreation.com)**

| | |
|---|---|
| **XpertAcademy** | Five courses — Word, Excel, PowerPoint, VBA, and Quranic Arabic. 67 lessons, quizzes, and certificates anyone can verify. |
| **Blood Bank** | Find a donor, or register as one. A donor's number is never listed; it is released once, by them, to one requester. |
| **Typing Tutor** | Fifteen drills, timed tests, and a falling-word game. Speed is measured on the server. |
| **Games** | Memory match and tic-tac-toe, with a leaderboard. |
| **Birthday Reminders** | Save the birthdays you forget. Email a few days before, and on the day. |
| **Weather** | Today and five days ahead, for any city. |

Twelve languages throughout, with right-to-left support for Urdu and Arabic.

---

## Why the code looks like this

A few decisions run through the whole project. They are here because the
earlier version got them wrong, and the difference matters.

**Scores are worked out on the server.** The typing tutor sends the text that
was actually typed, not a words-per-minute figure. Games send moves, not
points. A leaderboard built on numbers the browser chose is decoration.

**Quiz answers never reach the browser.** Questions are drawn from a pool and
graded server-side, so the correct answers are not sitting in the page for
anyone who opens developer tools.

**A donor's phone number is not in the search results.** It is attached to one
accepted request, for one requester, and every release is recorded. The
previous build returned two thousand numbers in a single unauthenticated
request — which is how a blood bank stops being usable by the people who need
it most.

**Certificates are earned, never created.** `has_add_permission = False` on the
admin, so nobody can mint one. Every certificate carries a serial that anyone
can check at `/verify` without an account.

**Coordinates are rounded before they are stored.** Two decimal places, about
1.1 km. Enough to sort donors by distance; not enough to find a house.

---

Chat is never open to strangers. A conversation starts only after both people have agreed to something: an accepted connection, blood request or donation. Nobody can message a member out of the blue.

The TMDB key never reaches the browser. Every film and drama request goes through the server and is cached, so the key stays private and the site stays fast.

A pet's tag page shows only what the owner chose. Anyone who finds a pet can leave a note without an account; the owner gets it at once, and their own details stay private unless they added a phone number themselves.

Business tools keep their data on the device. Employee lists, stock and attendance are stored in the browser, not on our server, because a shop's staff records are not ours to hold.

## Running it

Python 3.10+, PostgreSQL, Redis.

```bash
git clone https://github.com/khalidxpert/xpertcreation.git
cd xpertcreation
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then fill it in
python manage.py migrate
python manage.py seed_academy
python manage.py seed_typing
python manage.py createsuperuser
python manage.py runserver
```

`.env` needs a `SECRET_KEY`, database credentials, and SMTP details for the
sign-up codes. Weather works without a key — it uses open-meteo.

The front end is plain HTML, one file per app, no build step. They live in a
separate repository because they are deployed as static files.

### The daily jobs

```
0 8 * * *  manage.py send_birthday_reminders
0 9 * * *  manage.py pets_remind
```

Safe to run more than once: each reminder is sent once per year and logged.

---

## Apps

```
accounts/      sign-up, email codes, avatars, deletion
academy/       courses, lessons, quizzes, certificates
typingtutor/   drills, server-timed WPM, leaderboard
bloodbank/     donors, requests, consent-gated contact
reminders/     birthdays and the daily send
weather/       open-meteo, cached
games/         memory match, tic-tac-toe
network/       professional profiles, skills, endorsements, connections, follows, blue tick
notifications/ the bell, and chat that opens only after both people agree
pets/          pet profiles, health records, vaccine reminders, QR tags, lost and found
screen/        Pakistani and Indian dramas and films (TMDB), reviews, watchlists
donations/     giving and asking for things; chat once a request is accepted
vcard/         digital visiting cards
botlink/       linking an account to a messaging bot
frontend/      the site and XpertAcademy: plain HTML, CSS and JavaScript
```

The typing app is `typingtutor`, not `typing`. A folder called `typing` in the
project root shadows Python's own module of that name and breaks `asyncio`,
which stops `manage.py` from running at all. The error appears somewhere else
entirely, so it is worth knowing in advance.

---

## Contributing

Issues and pull requests are welcome. Two things to know:

The course content in `academy/` is written material, not generated. If you are
correcting a lesson, say what is wrong rather than replacing the text
wholesale. The Quranic Arabic course in particular carries Arabic that must not
be altered.

Anything touching scores, certificates or donor contact details should keep the
server as the source of truth. If a change moves a decision to the client, it
needs a good reason.

---

## Licence

AGPL-3.0. You can use, change and redistribute this. If you run a modified
version as a network service, you have to publish your changes too.

That is deliberate: this exists so people can run it, not so someone can wrap
it and sell access to a blood bank.

---

Built by [XpertCreation](https://xpertcreation.com), Lahore.
