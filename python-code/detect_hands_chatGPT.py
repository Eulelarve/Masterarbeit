import cv2
import mediapipe as mp


class HandTracker:
    def __init__(
        self,
        mode="both",  # "top", "left", "right", "both"
        max_num_hands=2,
        detection_confidence=0.7,
        tracking_confidence=0.5
    ):
        self.mode = mode

        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

    def _get_topmost_hand(self, multi_hand_landmarks):
        """
        Gibt die Hand zurück, deren Mittelpunkt
        am weitesten oben im Bild liegt.
        """

        best_hand = None
        best_y = float("inf")

        for hand_landmarks in multi_hand_landmarks:

            mean_y = sum(
                lm.y for lm in hand_landmarks.landmark
            ) / len(hand_landmarks.landmark)

            if mean_y < best_y:
                best_y = mean_y
                best_hand = hand_landmarks

        return best_hand

    def process(self, frame, draw=True):

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        if results.multi_hand_landmarks:
            print('len:', len(results.multi_hand_landmarks)) #test

        selected_hands = []

        if (
            results.multi_hand_landmarks
            and results.multi_handedness
        ):

            # --------------------------------------------------
            # Beide Hände
            # --------------------------------------------------

            if self.mode == "both":

                selected_hands = (
                    results.multi_hand_landmarks
                )

            # --------------------------------------------------
            # Oberste Hand
            # --------------------------------------------------

            elif self.mode == "top":

                top_hand = self._get_topmost_hand(
                    results.multi_hand_landmarks
                )

                if top_hand is not None:
                    selected_hands.append(top_hand)

            # --------------------------------------------------
            # Linke oder rechte Hand
            # --------------------------------------------------

            elif self.mode in ("left", "right"):

                desired_label = self.mode.capitalize()

                for hand_landmarks, handedness in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness
                ):

                    label = (
                        handedness.classification[0].label
                    )

                    if label == desired_label:
                        selected_hands.append(
                            hand_landmarks
                        )

        # ------------------------------------------------------
        # Zeichnen
        # ------------------------------------------------------

        if draw:

            for hand_landmarks in selected_hands:

                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )

        return frame, selected_hands, results


def main(c):

    # Mögliche Modi:
    # "top"
    # "left"
    # "right"
    # "both"

    tracker = HandTracker(
        mode="top"
    )

    cap = cv2.VideoCapture(c)
    paused = False
    last_results = None

    while True:

        if not paused:

            success, frame = cap.read()

            if not success:
                break

            frame = cv2.flip(frame, 1)

            frame, hands, results = tracker.process(
                frame,
                draw=True
            )

            last_results = results
        
        status = "PAUSED" if paused else "LIVE"

        cv2.putText(
            frame,
            f"Mode: {tracker.mode}",
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        cv2.imshow(
            "MediaPipe Hands",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == ord("1"):
            tracker.mode = "top"

        elif key == ord("2"):
            tracker.mode = "left"

        elif key == ord("3"):
            tracker.mode = "right"

        elif key == ord("4"):
            tracker.mode = "both"
        
        # Handlandmarks ausgeben
        elif key == ord(" "):

            if (
                last_results is not None and
                last_results.multi_hand_landmarks
            ):

                print("\n========== HAND LANDMARKS ==========")

                for hand_idx, hand in enumerate(
                    last_results.multi_hand_landmarks
                ):

                    print(f"\nHand {hand_idx}")

                    for lm_idx, lm in enumerate(
                        hand.landmark
                    ):

                        print(
                            f"{lm_idx:2d}: "
                            f"x={lm.x:.4f}, "
                            f"y={lm.y:.4f}, "
                            f"z={lm.z:.4f}"
                        )
                print("-----------------------------------")
                for e in results.multi_hand_landmarks[0].landmark: 
                    print([e], '#'*10)
                    # for lm in e:
                    #     print([lm], '#'*10)
                print("-----------------------------------")
                print([e for e in results.multi_handedness])
                print("===================================")
            else:
                print("Keine Hand erkannt.")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main(1)