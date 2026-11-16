import cv2
import math
import datetime
import settings

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17)
]

LEFT_IRIS = [468,469,470,471,472]
RIGHT_IRIS = [473,474,475,476,477]


class Renderer:

    def __init__(self):

        self.cyan = settings.CYAN
        self.green = settings.GREEN
        self.white = settings.WHITE
        self.blue = settings.BLUE

    def greeting(self):

        h = datetime.datetime.now().hour

        if h < 12:
            return "Good Morning"

        elif h < 17:
            return "Good Afternoon SIR"

        return "Good Evening SIR"

    def draw(self, frame, hand, face, gesture, fps):

        H, W, _ = frame.shape

        overlay = frame.copy()

        if settings.SHOW_HUD:

            cv2.rectangle(
                overlay,
                (10,10),
                (520,250),
                (15,18,28),
                -1
            )

            frame = cv2.addWeighted(
                overlay,
                0.55,
                frame,
                0.45,
                0
            )

            cv2.putText(
                frame,
                "JARVIS  ::  GestureMouse Pro",
                (25,35),
                cv2.FONT_HERSHEY_DUPLEX,
                0.72,
                self.cyan,
                2
            )

            cv2.putText(
                frame,
                self.greeting()+" Akshansh Sir",
                (25,65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                self.white,
                2
            )

            cv2.putText(
                frame,
                "MODE : "+settings.MODE_NAME[settings.CURRENT_MODE],
                (25,95),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                self.green,
                2
            )

            cv2.putText(
                frame,
                "GESTURE : "+gesture,
                (25,125),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                self.cyan,
                2
            )

            cv2.putText(
                frame,
                "ACTION : "+settings.LAST_ACTION,
                (25,155),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                self.white,
                2
            )

            cv2.putText(
                frame,
                "FPS : "+str(int(fps)),
                (25,185),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                self.green,
                2
            )

            cv2.putText(
                frame,
                datetime.datetime.now().strftime("%H:%M:%S"),
                (25,215),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                self.white,
                2
            )

        if settings.SHOW_IMPACT and hasattr(settings, "IMPACT_SNAPSHOT"):
            snapshot = settings.IMPACT_SNAPSHOT
            x = 18
            y = H - 142
            panel_width = min(560, max(360, W - 36))
            panel = frame.copy()
            cv2.rectangle(panel, (x, y), (x + panel_width, H - 30), (12, 18, 28), -1)
            frame = cv2.addWeighted(panel, 0.82, frame, 0.18, 0)
            accent = self.green if snapshot["complete"] else self.cyan
            title = f"IMPACT MODE  //  {snapshot['title']}"
            cv2.putText(frame, title, (x + 16, y + 28), cv2.FONT_HERSHEY_DUPLEX, 0.62, accent, 2)
            cv2.putText(frame, snapshot["prompt"], (x + 16, y + 56), cv2.FONT_HERSHEY_SIMPLEX, 0.54, self.white, 1)
            cv2.putText(
                frame,
                f"PROOF  {snapshot['score']}%   STEP {snapshot['step']}/{snapshot['total']}   LAST {snapshot['last_event']}",
                (x + 16, y + 86),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                self.white,
                1,
            )
            cv2.rectangle(frame, (x + 16, y + 102), (x + panel_width - 16, y + 110), (55, 65, 75), -1)
            cv2.rectangle(
                frame,
                (x + 16, y + 102),
                (x + 16 + int((panel_width - 32) * snapshot["score"] / 100), y + 110),
                accent,
                -1,
            )

        # =======================
        # HAND RENDER
        # =======================

        if hand is not None and settings.SHOW_HAND:

            pulse = int(
                6 + 3 * math.sin(
                    datetime.datetime.now().timestamp()*6
                )
            )

            for a,b in HAND_CONNECTIONS:

                p1 = hand[a]
                p2 = hand[b]

                x1 = int(p1.x*W)
                y1 = int(p1.y*H)

                x2 = int(p2.x*W)
                y2 = int(p2.y*H)

                cv2.line(
                    frame,
                    (x1,y1),
                    (x2,y2),
                    self.cyan,
                    2
                )

            for lm in hand:

                x = int(lm.x*W)
                y = int(lm.y*H)

                cv2.circle(
                    frame,
                    (x,y),
                    pulse+5,
                    self.cyan,
                    2
                )

                cv2.circle(
                    frame,
                    (x,y),
                    pulse,
                    self.blue,
                    -1
                )

                cv2.circle(
                    frame,
                    (x,y),
                    3,
                    self.white,
                    -1
                )
                # =======================

        cv2.putText(
            frame,
            "AKSHANSH  //  ORIGINAL AUTHOR",
            (max(16, W - 390), H - 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            self.white,
            1,
            cv2.LINE_AA
        )
        # FACE / EYE HUD
        # =======================

        if face is not None and settings.SHOW_FACE:

            # LEFT IRIS

            xs = []
            ys = []

            for i in LEFT_IRIS:

                if i < len(face):

                    xs.append(int(face[i].x * W))
                    ys.append(int(face[i].y * H))

            if xs:

                cx = sum(xs)//len(xs)
                cy = sum(ys)//len(ys)

                cv2.circle(frame,(cx,cy),22,self.cyan,2)
                cv2.circle(frame,(cx,cy),8,self.white,2)

                cv2.line(frame,(cx-30,cy),(cx-12,cy),self.cyan,1)
                cv2.line(frame,(cx+12,cy),(cx+30,cy),self.cyan,1)
                cv2.line(frame,(cx,cy-30),(cx,cy-12),self.cyan,1)
                cv2.line(frame,(cx,cy+12),(cx,cy+30),self.cyan,1)

            # RIGHT IRIS

            xs=[]
            ys=[]

            for i in RIGHT_IRIS:

                if i < len(face):

                    xs.append(int(face[i].x * W))
                    ys.append(int(face[i].y * H))

            if xs:

                cx=sum(xs)//len(xs)
                cy=sum(ys)//len(ys)

                cv2.circle(frame,(cx,cy),22,self.cyan,2)
                cv2.circle(frame,(cx,cy),8,self.white,2)

                cv2.line(frame,(cx-30,cy),(cx-12,cy),self.cyan,1)
                cv2.line(frame,(cx+12,cy),(cx+30,cy),self.cyan,1)
                cv2.line(frame,(cx,cy-30),(cx,cy-12),self.cyan,1)
                cv2.line(frame,(cx,cy+12),(cx,cy+30),self.cyan,1)

        # =======================
        # CYBER CORNERS
        # =======================

        s = 35
        c = self.cyan

        cv2.line(frame,(0,s),(0,0),c,2)
        cv2.line(frame,(0,0),(s,0),c,2)

        cv2.line(frame,(W-s,0),(W,0),c,2)
        cv2.line(frame,(W,0),(W,s),c,2)

        cv2.line(frame,(0,H-s),(0,H),c,2)
        cv2.line(frame,(0,H),(s,H),c,2)

        cv2.line(frame,(W-s,H),(W,H),c,2)
        cv2.line(frame,(W,H-s),(W,H),c,2)

        # =======================
        # CONTROLS PANEL
        # =======================

        if settings.SHOW_CONTROLS:

            x = W - 235
            y = 20

            overlay = frame.copy()

            cv2.rectangle(
                overlay,
                (x-15,y-10),
                (W-15,310),
                (18,18,25),
                -1
            )

            frame = cv2.addWeighted(
                overlay,
                0.55,
                frame,
                0.45,
                0
            )

            cv2.putText(
                frame,
                "COMMANDS",
                (x,40),
                cv2.FONT_HERSHEY_DUPLEX,
                0.72,
                self.cyan,
                2
            )

            yy = 70

            for cmd in settings.CONTROLS:

                cv2.putText(
                    frame,
                    cmd,
                    (x,yy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    self.white,
                    1
                )

                yy += 22

        return frame