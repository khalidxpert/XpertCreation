from django.core.management.base import BaseCommand
from django.db import transaction

from typingtutor.models import Drill

DRILLS = {
 "lessons": [
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row: a s d f",
   "hint": "Left hand. Fingers rest on a s d f — do not look down.",
   "content": "asdf fdsa asdf fdsa aasd ssdf ddfa ffas asdf fdsa sada fada dasf safd asdf fdsa",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row: j k l ;",
   "hint": "Right hand. Fingers rest on j k l ; — keep the wrists still.",
   "content": "jkl; ;lkj jkl; ;lkj jjkl kkl; ll;j ;;jk jkl; ;lkj lkja kjl; jklj ;lkj jkl;",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row together",
   "hint": "Both hands. Return to the home row after every key.",
   "content": "asdf jkl; fdsa ;lkj as jk df kl sad lad fad ask lass fall flask salad; dad had sad; jak lad; all fall; a lad asks",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row words",
   "hint": "Real words, home row only. Aim for a steady rhythm, not speed.",
   "content": "flask salad dad lad sad fall gall hall skald aslash a sad lad has half a flask; all lads fall; dad asks a lass",
   "lang": "en",
   "order": 3
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Top row: e r u i",
   "hint": "Reach up, then come straight back to the home row.",
   "content": "ere rer uiu iui deer reed used ride ideas users irked here we ride; use the reed; deer are here",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Top row: q w t y o p",
   "hint": "The outer reaches. Slow down — accuracy first.",
   "content": "qwt yop pot toy two type quote wrote power topic yellow we type two quotes; the toy pot; power to type",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Home and top rows",
   "hint": "Now mix them. Do not look at the keyboard.",
   "content": "the quiet street was full of people who wrote letters he wrote a report; she typed the letter; they read it out",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "Bottom row: z x c v",
   "hint": "Left hand drops down. Keep the other fingers home.",
   "content": "zxc vzx cvz xcv zac cave vex crazy exact voice cover a crazy cave; exact voice; cover the box",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "Bottom row: b n m , .",
   "hint": "Right hand drops down. Comma and full stop matter.",
   "content": "bnm ,.b mnb .,m number member, bomb, month. the number, the member, the month.",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "All three rows",
   "hint": "Everything so far. Slow, correct, then faster.",
   "content": "the black cat moved between the boxes and the number of members grew month by month, quietly and without much fuss.",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 4,
   "title": "Capitals",
   "hint": "Hold Shift with the opposite hand from the letter.",
   "content": "Ali Sara Lahore Karachi Islamabad Pakistan Monday March Ali lives in Lahore. Sara works in Karachi.",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 4,
   "title": "Punctuation",
   "hint": "Apostrophes, question marks, brackets.",
   "content": "don't can't it's we're (yes) [no] \"quoted\" 'single' Isn't it done? It's nearly finished (almost).",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "Numbers 1 to 5",
   "hint": "Left hand reaches for the top number row.",
   "content": "1 2 3 4 5 11 22 33 44 55 123 234 345 in 2015 we had 34 members and 12 rooms",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "Numbers 6 to 0",
   "hint": "Right hand. Do not look up.",
   "content": "6 7 8 9 0 66 77 88 99 00 678 890 call 0300 946 2916 on 9 August 2026",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "Numbers and symbols",
   "hint": "The row above the letters, in full.",
   "content": "50% of 200 is 100. Email: hello@site.com. Cost: $45 + 17% tax = $52.65.",
   "lang": "en",
   "order": 2
  }
 ],
 "tests": [
  {
   "kind": "test",
   "level": 1,
   "title": "Short test",
   "hint": "About one minute of typing.",
   "content": "The quick brown fox jumps over the lazy dog. Every letter of the alphabet appears in that sentence, which is why typists have used it for a very long time to check that each key works and each finger knows where to go.",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "test",
   "level": 2,
   "title": "Medium test",
   "hint": "About two minutes.",
   "content": "Learning to type without looking takes patience more than talent. The trick is to slow down until your fingers stop guessing. Speed arrives on its own once the hands know where the keys are, and it arrives faster for people who practise for ten minutes every day than for people who practise for two hours once a week.",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "test",
   "level": 2,
   "title": "Numbers and punctuation",
   "hint": "Mixed content, harder than plain text.",
   "content": "In 2026 the office moved to 14 Ghazali Park, and the phone number changed to 0300-946-2916. Rent went up by 12%, from 35,000 to 39,200 a month. \"It is what it is,\" the manager said, \"but we're staying put.\"",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "test",
   "level": 3,
   "title": "Long test",
   "hint": "About five minutes. Keep a steady pace.",
   "content": "Most people type faster than they think they can, but less accurately than they believe. A typist at sixty words a minute with ninety percent accuracy is slower, in practice, than one at fifty with ninety-eight, because every mistake costs more than the keystroke that made it. You have to notice it, go back, delete it and type it again. That is four actions to undo one. This is why every serious typing course insists on accuracy first and speed later, and why the students who ignore that advice plateau early and stay there, wondering what went wrong.",
   "lang": "en",
   "order": 3
  }
 ],
 "games": [
  {
   "kind": "game",
   "level": 1,
   "title": "Letter rain",
   "hint": "Single letters fall. Type each one before it lands.",
   "content": "a s d f j k l g h e r u i t y o p q w z x c v b n m",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "game",
   "level": 2,
   "title": "Word rain",
   "hint": "Short words fall. Type each one and press space.",
   "content": "cat dog sun run top ask lad sad fan map bed cup pen key box win jam fig owl ink hat leg cow pig art oak bus car day eye far gap hen ice",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "game",
   "level": 3,
   "title": "Fast words",
   "hint": "Longer words, falling quicker.",
   "content": "letter number market travel window person animal school family garden morning evening picture teacher student machine science history country problem chapter journey freedom program library",
   "lang": "en",
   "order": 2
  }
 ]
}


class Command(BaseCommand):
    help = "Create or update the typing drills. Safe to re-run."

    @transaction.atomic
    def handle(self, *args, **opts):
        made = updated = 0
        for group in ("lessons", "tests", "games"):
            for i, d in enumerate(DRILLS[group]):
                obj, created = Drill.objects.update_or_create(
                    kind=d["kind"], level=d["level"], title=d["title"],
                    defaults={"hint": d["hint"], "content": d["content"],
                              "lang": d["lang"], "order": d["order"],
                              "is_active": True},
                )
                made += created
                updated += (not created)
            self.stdout.write("  %-8s %d" % (group, len(DRILLS[group])))
        self.stdout.write(self.style.SUCCESS(
            "Done. created %d, updated %d, total %d" % (made, updated, Drill.objects.count())))
