from django.core.management.base import BaseCommand
from django.db import transaction

from typingtutor.models import Drill

DRILLS = {
 "lessons": [
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row: left hand",
   "hint": "Fingers rest on a s d f. Do not look down.",
   "content": "asdf fdsa asdf fdsa aasd ssdf ddfa ffas asdf fdsa sada fada dasf safd asdf fads dfas sdaf afds asdf fdsa adfs sfda dasa fasf sada dafs asdf fdsa aa ss dd ff aa ss dd ff asdf fdsa asdf fdsa",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row: right hand",
   "hint": "Fingers rest on j k l semicolon. Wrists still.",
   "content": "jkl; ;lkj jkl; ;lkj jjkl kkl; ll;j ;;jk jkl; ;lkj lkja kjl; jklj ;lkj jj kk ll ;; jj kk ll ;; jkl; ;lkj klj; ;jlk jkl; ;lkj jkl; ;lkj lkj; ;jkl jlk; ;klj jkl; ;lkj",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Both hands together",
   "hint": "Return to the home row after every key.",
   "content": "asdf jkl; fdsa ;lkj as jk df kl sad lad fad ask lass fall flask salad dad had sad jak lad all fall a lad asks a lass half daff gall hall skald aslash asks falls lads adds asdf jkl; fdsa ;lkj asdf jkl; fdsa ;lkj",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row: g and h",
   "hint": "The two keys your index fingers reach for.",
   "content": "fgf jhj fgf jhj gg hh gag hah gas has gash hash flag half glad shall gala halls flags glass hall gash a glad lass has half a flag fgf jhj fgf jhj gaff hajj gash halls",
   "lang": "en",
   "order": 3
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row words",
   "hint": "Real words, home row only. Rhythm before speed.",
   "content": "flask salad dad lad sad fall gall hall skald aslash glass a sad lad has half a flask all lads fall dad asks a lass glad flags halls glass shall gash flash add all ask dad fad gas had half hall lad lash sad salad",
   "lang": "en",
   "order": 4
  },
  {
   "kind": "lesson",
   "level": 1,
   "title": "Home row sentences",
   "hint": "Slow and correct. Speed comes later on its own.",
   "content": "a lad had a flask. dad asks a lass. all glass falls. half a salad; half a flask. a glad lass shall dash. sad lads ask dad. gall flags fall. a flask fads. dad had a glass; a lass had a salad; all lads shall dash.",
   "lang": "en",
   "order": 5
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Top row: e and r",
   "hint": "Reach up, come straight back.",
   "content": "ded frf ded frf ee rr deer reed dear read fear rear here red fed her err freed reeds hears feared a red deer feared her. she freed a reed. ded frf ded frf reed deer here read",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Top row: u and i",
   "hint": "Right hand reaches. Keep the others home.",
   "content": "juj kik juj kik uu ii juice quiet issue fluid liquid just like unit fruit build guild suit ruin juj kik just like fruit quiet fluid issue",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Top row: t and y",
   "hint": "Two more index-finger reaches.",
   "content": "ftf jyj ftf jyj tt yy the they that type try duty tidy study yet let type the tray they try the tidy tray. that duty is yours. ftf jyj type they that study",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Top row: q w o p",
   "hint": "The outer reaches. Accuracy first, always.",
   "content": "aqa sws lol ;p; qq ww oo pp quit wall look pool power quote wrote topic yellow prop stop swap we quit the pool. she wrote a quote. aqa sws lol ;p; quit wall look pool power",
   "lang": "en",
   "order": 3
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Home and top rows",
   "hint": "Mix them. Do not look at the keyboard.",
   "content": "the quiet street was full of people who wrote letters he wrote a report. she typed the letter. they read it out. our house has three doors. the water is quite hot today. we should try the other road. it is a shorter route.",
   "lang": "en",
   "order": 4
  },
  {
   "kind": "lesson",
   "level": 2,
   "title": "Common words",
   "hint": "The hundred words you type most often.",
   "content": "the of and to a in is you that it he was for on are as with his they at be this have from or one had by word but not what all were we when your can said there use an each which she do how their if will up other",
   "lang": "en",
   "order": 5
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "Bottom row: z x c",
   "hint": "Left hand drops. Others stay home.",
   "content": "aza sxs dcd aza sxs dcd zz xx cc zac cave exact zeal exit cause crazy voice excel czar a crazy czar. exact cause. we excel at zeal. aza sxs dcd zac cave exact crazy",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "Bottom row: v and b",
   "hint": "Index fingers drop down and back.",
   "content": "fvf fbf fvf fbf vv bb verb vibe brave above very base best above verb obey bulb vast a brave verb. the best base. very vast. fvf fbf verb vibe brave above obey",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "Bottom row: n and m",
   "hint": "Right hand drops. Do not look.",
   "content": "jnj jmj jnj jmj nn mm noun month name mean man men main mine name none numb moan many men name the month. mine is none. jnj jmj noun month name mean numb",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "Comma and full stop",
   "hint": "Punctuation lives on the bottom row too.",
   "content": "k,k l.l k,k l.l ,, .. one, two, three. stop. go. yes, no, maybe. first, second, third. he came, he saw, he left. it is done. k,k l.l one, two. red, blue. now, then.",
   "lang": "en",
   "order": 3
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "All three rows",
   "hint": "Everything so far. Slow, correct, then faster.",
   "content": "the black cat moved between the boxes and the number of members grew month by month, quietly and without much fuss. many brave men have named the mountain, but nobody can prove which name came first, or when.",
   "lang": "en",
   "order": 4
  },
  {
   "kind": "lesson",
   "level": 3,
   "title": "Mixed practice",
   "hint": "No pattern. Just type.",
   "content": "quick brown foxes jump over lazy dogs every evening. amazing vocabulary requires extra practice, but the effort pays back quickly. seven zebras crossed the vast plain before dawn, moving without a sound.",
   "lang": "en",
   "order": 5
  },
  {
   "kind": "lesson",
   "level": 4,
   "title": "Capitals: left hand",
   "hint": "Shift with the opposite hand from the letter.",
   "content": "Ali Sara Ahmed Bilal Danish Farah Gul Hina Lahore Karachi Islamabad Multan Quetta Peshawar Ali lives in Lahore. Sara works in Karachi. Bilal and Danish went to Multan on Friday.",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 4,
   "title": "Capitals: right hand",
   "hint": "Left shift for right-hand letters.",
   "content": "Umar Nadia Maria Junaid Osman Pakistan Punjab Monday Tuesday March April July October Umar met Nadia in Punjab last March. On Monday, Osman flew to Islamabad.",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 4,
   "title": "Apostrophes",
   "hint": "The key beside the semicolon.",
   "content": "don't can't it's we're I'm you're they're won't isn't wasn't haven't couldn't shouldn't didn't It's done. We're leaving. Don't worry, it isn't far. I'm sure they're coming, but he couldn't say when.",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 4,
   "title": "Quotes and brackets",
   "hint": "Shift for the upper symbols.",
   "content": "\"yes\" 'no' (maybe) [later] {never} \"quoted text\" He said, \"It is finished.\" She replied, \"Good.\" The result (see page 4) was clear. \"Isn't it done?\" she asked. \"Nearly,\" he said.",
   "lang": "en",
   "order": 3
  },
  {
   "kind": "lesson",
   "level": 4,
   "title": "Full punctuation",
   "hint": "Everything together.",
   "content": "Isn't it done? It's nearly finished (almost). The meeting - moved twice already - starts at 9:30. \"We can't wait,\" he said; \"it's been three weeks.\" Send it to: ali@example.com, then call 0300-946-2916.",
   "lang": "en",
   "order": 4
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "Numbers 1 to 5",
   "hint": "Left hand reaches for the number row.",
   "content": "1 2 3 4 5 11 22 33 44 55 123 234 345 12345 1a 2s 3d 4f 5g 15 25 35 45 in 2015 we had 34 members and 12 rooms 1 2 3 4 5 54321 12345 135 245",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "Numbers 6 to 0",
   "hint": "Right hand. Do not look up.",
   "content": "6 7 8 9 0 66 77 88 99 00 678 890 67890 6j 7k 8l 9; 0p 69 78 89 90 call 0300 946 2916 on 9 August 2026 6 7 8 9 0 09876 67890 680 790",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "All ten digits",
   "hint": "Mix them. This is the row people avoid.",
   "content": "1234567890 0987654321 1590 2680 3570 4680 invoice 4471 dated 09/08/2026 for 15,300 rooms 101, 204, 307 and 412 are booked 1029 3847 5601 7382 9450 1827",
   "lang": "en",
   "order": 2
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "Symbols",
   "hint": "The row above the letters, with shift.",
   "content": "! @ # $ % ^ & * ( ) - _ = + 50% of 200 is 100. Cost: $45 + 17% tax = $52.65. Email: hello@site.com  File: report_final_v2.pdf 5 * 4 = 20 and 100 / 4 = 25 (roughly)",
   "lang": "en",
   "order": 3
  },
  {
   "kind": "lesson",
   "level": 5,
   "title": "Real world typing",
   "hint": "Everything at once, like actual work.",
   "content": "Invoice #4471, dated 09/08/2026: 15 units @ Rs. 2,300 = Rs. 34,500 plus 17% GST (Rs. 5,865), total Rs. 40,365. Contact: accounts@xpertcreation.com or 0300-946-2916. Payment due within 30 days; late fees apply after that.",
   "lang": "en",
   "order": 4
  }
 ],
 "tests": [
  {
   "kind": "test",
   "level": 1,
   "title": "One minute",
   "hint": "A short warm-up.",
   "content": "The quick brown fox jumps over the lazy dog. Every letter of the alphabet appears in that sentence, which is why typists have used it for a very long time to check that each key works and each finger knows where to go.",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "test",
   "level": 1,
   "title": "One minute: common words",
   "hint": "The words you type most.",
   "content": "It is not the speed that matters at first, but whether your hands know where they are going without you telling them. That comes from doing the same short thing every day, not from doing a long thing once a week.",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "test",
   "level": 2,
   "title": "Two minutes",
   "hint": "Settle into a rhythm.",
   "content": "Learning to type without looking takes patience more than talent. The trick is to slow down until your fingers stop guessing. Speed arrives on its own once the hands know where the keys are, and it arrives faster for people who practise for ten minutes every day than for people who practise for two hours once a week. The difference is not effort. It is repetition, spread out, until the movement stops needing thought.",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "test",
   "level": 2,
   "title": "Two minutes: numbers",
   "hint": "Mixed content, harder than plain text.",
   "content": "In 2026 the office moved to 14 Ghazali Park, and the phone number changed to 0300-946-2916. Rent went up by 12%, from 35,000 to 39,200 a month. \"It is what it is,\" the manager said, \"but we're staying put.\" The lease runs to March 2029, with a 6-month notice period on either side, and the deposit of 78,400 is held against damage rather than rent.",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "test",
   "level": 3,
   "title": "Five minutes",
   "hint": "Keep a steady pace all the way through.",
   "content": "Most people type faster than they think they can, but less accurately than they believe. A typist at sixty words a minute with ninety percent accuracy is slower, in practice, than one at fifty with ninety-eight, because every mistake costs more than the keystroke that made it. You have to notice it, go back, delete it and type it again. That is four actions to undo one. This is why every serious typing course insists on accuracy first and speed later, and why the students who ignore that advice plateau early and stay there, wondering what went wrong. The fix is dull and it works: slow down until you stop making errors, hold that pace until it feels easy, then let it rise on its own. It always does.",
   "lang": "en",
   "order": 0
  },
  {
   "kind": "test",
   "level": 3,
   "title": "Five minutes: mixed",
   "hint": "Text, numbers and punctuation together.",
   "content": "The report covering the period from 1 April to 30 September 2026 shows revenue of Rs. 4,382,000 against a forecast of Rs. 4,100,000 - an increase of 6.9%. Costs rose more sharply, from Rs. 2,940,000 to Rs. 3,215,000 (9.4%), largely because of the move to 14 Ghazali Park and the associated fit-out. \"We expected the second half to be tighter,\" the finance lead wrote, \"but not by this much.\" Headcount stayed flat at 23. The board meets on 14 December to review the 2027 budget, and the deadline for submissions is 30 November at 5pm.",
   "lang": "en",
   "order": 1
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
   "hint": "Short words. Type each one as it falls.",
   "content": "cat dog sun run top ask lad sad fan map bed cup pen key box win jam fig owl ink hat leg cow pig art oak bus car day eye far gap hen ice job lip mud net oil pot rat sea tin van wax yes zip bag",
   "lang": "en",
   "order": 1
  },
  {
   "kind": "game",
   "level": 3,
   "title": "Fast words",
   "hint": "Longer words, falling quicker.",
   "content": "letter number market travel window person animal school family garden morning evening picture teacher student machine science history country problem chapter journey freedom program library measure quarter distance evidence practice sentence attention",
   "lang": "en",
   "order": 2
  }
 ]
}


class Command(BaseCommand):
    help = "Create or update the typing drills. Safe to re-run."

    def handle(self, *args, **opts):
        with transaction.atomic():
            made = updated = 0
            for group in ("lessons", "tests", "games"):
                for d in DRILLS[group]:
                    obj, created = Drill.objects.update_or_create(
                        kind=d["kind"], level=d["level"], title=d["title"],
                        defaults={"hint": d["hint"], "content": d["content"],
                                  "lang": d["lang"], "order": d["order"],
                                  "is_active": True},
                    )
                    made += created
                    updated += (not created)
                self.stdout.write("  %-8s %d" % (group, len(DRILLS[group])))

            # Drills no longer in this file are switched off rather than
            # deleted: someone's saved progress may still point at them.
            titles = [d["title"] for g in DRILLS.values() for d in g]
            stale = Drill.objects.exclude(title__in=titles)
            if stale.exists():
                n = stale.update(is_active=False)
                self.stdout.write("  retired %d old drill(s)" % n)

        self.stdout.write(self.style.SUCCESS(
            "created %d, updated %d, active %d"
            % (made, updated, Drill.objects.filter(is_active=True).count())))
