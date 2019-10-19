import unittest
import os
import shutil
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from viewcontrol import show


class TestShow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.project_folder = os.path.expanduser("testing")
        if os.path.exists(cls.project_folder):
            shutil.rmtree(cls.project_folder)

    @classmethod
    def tearDownClass(cls):
        #shutil.rmtree(cls.project_folder)
        return

    def setUp(self):
        self.show = show.Show(TestShow.project_folder)
        
    def test_1000_show(self):
        self.assertEqual(len(self.show.show_display), 0)
        self.show.show_new("testA")
        #still 0 because no element was created
        self.assertEqual(len(self.show.show_display), 0)
        self.show.add_module_text("test1", "test1", 1)
        self.assertEqual(len(self.show.show_display), 1)
        self.assertEqual(self.show.show_display[0], "testA")

    def test_1001_show(self):
        self.assertEqual(self.show.show_display[0], "testA")
        self.assertFalse(self.show.show_new("testA"))
        self.assertFalse(self.show.show_load("testB"))
        self.assertTrue(self.show.show_new("testB"))
        self.show.add_module_text("test2", "test2", 2)
        self.assertEqual(len(self.show.show_display), 2)
        self.assertTrue(self.show.show_close())

    def test_1002_show(self):
        self.assertTrue(self.show.show_delete("testA"))
        self.assertEqual(len(self.show.show_display), 1)
        self.assertFalse(self.show.show_load("testA"))
        self.assertEqual(self.show.show_display[0], "testB")
        self.assertIsNone(self.show.name_show)
        self.assertFalse(self.show.show_delete())
        self.assertTrue(self.show.show_load("testB"))
        self.assertTrue(self.show.show_delete())
        self.assertEqual(len(self.show.show_display), 0)

    def test_1003_show(self):
        self.assertEqual(len(self.show.show_display), 0)
        self.assertFalse(self.show.show_new("testA"))
        self.assertEqual(len(self.show.show_display), 0)
        self.assertFalse(self.show.show_new("testB"))
        self.assertEqual(len(self.show.show_display), 0)
        self.assertTrue(self.show.show_new("testC"))
        self.show.add_module_text("test3", "test3", 3)
        self.assertEqual(len(self.show.show_display), 1)
        self.assertFalse(self.show.show_load(None))


class TestShowPlaylist(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.project_folder = os.path.expanduser("testing")
        #if os.path.exists(cls.project_folder):
        #    shutil.rmtree(cls.project_folder)

    @classmethod
    def tearDownClass(cls):
        #shutil.rmtree(cls.project_folder)
        return

    def setUp(self):
        self.show = show.Show(TestShowPlaylist.project_folder)
        self.show.show_load("testing")
        print('')
        self.t_start = time.time()

    def tearDown(self):
        print("{:<40} - {} s".format(self._testMethodName, time.time()-self.t_start), sep="")

    def test_1000_show(self):
        #is show database created
        self.assertTrue(os.path.exists(self.project_folder+'/vcproject.db3'))
        self.assertEqual(self.show.count, 0)

    def test_1101_append_pdf_big(self):
        self.assertEqual(self.show.count, 0)
        self.show.show_new("testing")
        #add pdf, check if files are created        
        self.show.add_module_still("poster", "media/bbb_poster.pdf", 8)
        self.assertTrue(os.path.exists(self.project_folder+'/bbb_poster_w.jpg'))
        self.assertTrue(os.path.exists(self.project_folder+'/bbb_poster_c.jpg'))
        self.assertEqual(self.show.count, 1)

    def test_1102_append_same(self):
        self.assertEqual(self.show.count, 1)
        #add same (source-)file(name) twice , check if counter is added on files
        self.show.add_module_still("anouncement", "media/bbb_title_anouncement.jpg", 2)
        self.show.add_module_still("anouncement_copy", "media/bbb_title_anouncement.jpg", 3)
        self.assertTrue(os.path.exists(self.project_folder+'/bbb_title_anouncement_c.jpg'))
        self.assertTrue(os.path.exists(self.project_folder+'/bbb_title_anouncement_c_2.jpg'))
        self.assertTrue(os.path.exists(self.project_folder+'/bbb_title_anouncement_w.jpg'))
        self.assertTrue(os.path.exists(self.project_folder+'/bbb_title_anouncement_w_2.jpg'))
        self.assertEqual(self.show.count, 3)

    def test_1203_delete_same(self):
        self.assertEqual(self.show.count, 3)
        self.show.remove_module(2)
        self.assertEqual(self.show.count, 2)
        #self.assertEqual(self.media_elements)
        #check if obj is still in MEdiaElements

    def test_1213_append_identical_name(self):
        self.assertEqual(self.show.count, 2)
        #try to add same name twice. result should be a two behind name of 
        #second sequence module.
        self.show.add_module_still("bbb_picture", "media/bbb_poster_bunny_big.jpg", 5)
        self.show.add_module_still("bbb_picture", "media/bbb_poster_rodents_big.jpg", 5)
        bbb1 = self.show._get_module_with_element_name("bbb_picture")
        self.assertIsNotNone(bbb1)
        self.assertEqual(bbb1.media_element.file_path_c, "bbb_poster_bunny_big_c.jpg")
        bbb2 = self.show._get_module_with_element_name("bbb_picture_2")
        self.assertIsNotNone(bbb2)
        self.assertEqual(bbb2.media_element.file_path_c, "bbb_poster_rodents_big_c.jpg")
        self.assertEqual(self.show.count, 4)

    def test_1304_append_loop(self):
        self.assertEqual(self.show.count, 4)
        #add loop and change its position in playlist (this procedure shall be used in GUI to)
        self.show.add_module_loop(3, pos=3)
        self.assertEqual(self.show._get_module_with_element_name("#LoopStart_1").position, 3)
        self.assertEqual(self.show._get_module_with_element_name("#LoopEnd_1").position, 4)
        self.show.move_element_up(3)
        self.assertEqual(self.show._get_module_with_element_name("#LoopStart_1").position, 2)
        self.assertEqual(self.show._get_module_with_element_name("#LoopEnd_1").position, 4)
        self.show.move_element_down(4)
        self.assertEqual(self.show._get_module_with_element_name("#LoopStart_1").position, 2)
        self.assertEqual(self.show._get_module_with_element_name("#LoopEnd_1").position, 5)


    def test_1305_append_jumpto(self):
        self.assertEqual(self.show.count, 6)
        self.show.add_module_jumptotarget("skip loop", "event_key_end", 
            commands=show.Command(
                "dimm light", "CommandDmx", "Group10-Intesity", 30))
        self.assertEqual(self.show._get_module_at_pos(6).name, "#skip loop")
        self.assertEqual(self.show.count, 7)

    def test_1306_add_delete_another_jumpto(self):
        self.assertEqual(self.show.count, 7)
        self.show.add_module_jumptotarget("#skip loop", "event_xy")
        self.assertEqual(self.show._get_module_at_pos(7).name, "#skip loop_2")
        self.show.remove_module(7)
        self.assertEqual(self.show.count, 7)

    def test_1316_append_text_element(self):
        self.assertEqual(self.show.count, 7)
        self.show.add_module_text("next", "next at viewntrol", 5)
        self.assertTrue(os.path.exists(self.project_folder+'/_next.jpg'))
        self.assertEqual(self.show.count, 8)

    def test_1317_chnage_text(self):
        self.show.module_text_change_text(7, "next at viewcontrol")
        self.assertEqual(self.show._get_module_at_pos(7).media_element.text, "next at viewcontrol")

    def test_1320_append_video(self):
        commands=[
            show.Command("jump to start chapter", "CommandDenon", "Track Jump", 1),
            show.Command("swich video to BluRay", "CommandAtlona", "Set Output", 1, 2)]
        self.assertEqual(self.show.count, 8)
        self.show.add_module_video("clip2_kite", "media/Big_Buck_Bunny_1080p_clip2.avi", pos=8, commands=commands)
        self.show.add_module_video("clip1_apple", "media/Big_Buck_Bunny_1080p_clip.mp4", pos=8)
        self.assertTrue(os.path.exists(self.project_folder+'/Big_Buck_Bunny_1080p_clip2_c.mp4'))
        self.assertTrue(os.path.exists(self.project_folder+'/Big_Buck_Bunny_1080p_clip2_w.mp4'))
        self.assertTrue(os.path.exists(self.project_folder+'/Big_Buck_Bunny_1080p_clip_c.mp4'))
        self.assertTrue(os.path.exists(self.project_folder+'/Big_Buck_Bunny_1080p_clip_w.mp4'))
        self.assertEqual(self.show._get_module_with_element_name("clip2_kite").position, 9)
        self.assertEqual(self.show._get_module_with_element_name("clip1_apple").position, 8)
        self.assertEqual(len(self.show._get_module_with_element_name("clip2_kite").list_commands), 2)
        self.assertEqual(self.show.count, 10)

    def test_1401_add_command(self):
        self.assertEqual(self.show.count, 10)
        command2 = show.Command("swich video to PC", "CommandAtlona", "Set Output", 1, 3)
        self.show.add_command_to_pos(0, command2)
        self.assertEqual(len(self.show._get_module_at_pos(0).list_commands), 1)



if __name__ == '__main__':
    unittest.main(failfast=True)