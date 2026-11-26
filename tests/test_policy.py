import unittest
from app.policy import Policy

class ScalingTests(unittest.TestCase):
    def test_two_hot_samples_per_step(self):
        p=Policy()
        for count in (2,4):
            p.observe(count,70,10)
            self.assertEqual(count,p.desired)
            p.observe(count,70,12)
            self.assertEqual(count+2,p.desired)
        for _ in range(5): p.observe(6,100,20)
        self.assertEqual(6,p.desired)

    def test_cooldown_resets_on_rebound(self):
        p=Policy(desired=6)
        for t in (0,15,29): p.observe(6,5,t)
        self.assertEqual(6,p.desired)
        p.observe(6,27,30)
        p.observe(6,5,31)
        p.observe(6,5,60)
        self.assertEqual(6,p.desired)
        p.observe(6,5,61)
        self.assertEqual(2,p.desired)

    def test_missing_sample_holds(self):
        p=Policy(desired=4)
        for now in range(100):
            p.observe(2,None,now)
        self.assertEqual(4,p.desired)
