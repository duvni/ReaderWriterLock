import unittest
import threading
import time
from ReaderWriterLock import ReaderWriterLock


class WriterThread(threading.Thread):

    def __init__(self, rw_lock: ReaderWriterLock, lock_timeout: float, wait_timeout: float, working_list: list,
                 new_value):
        self.write_acquired = False
        self.write_lock_held = False
        self._rw_lock = rw_lock
        self._lock_timeout = lock_timeout
        self._wait_timeout = wait_timeout
        self.working_list = working_list
        self._new_value = new_value
        threading.Thread.__init__(self)

    def run(self):
        self.write_acquired = self._rw_lock.enter_write_lock(self._lock_timeout)
        self.write_lock_held = self._rw_lock.is_write_lock_held
        if not self.write_acquired:
            return
        time.sleep(self._wait_timeout)
        self.working_list[0] = self._new_value
        self._rw_lock.exit_write_lock()


class ReaderThread(threading.Thread):

    def __init__(self, rw_lock: ReaderWriterLock, lock_timeout: float, wait_timeout: float, working_list: list):
        self.read_acquired = False
        self.read_lock_held = False
        self._rw_lock = rw_lock
        self._lock_timeout = lock_timeout
        self._wait_timeout = wait_timeout
        self.working_list = working_list
        self.value_read = None
        threading.Thread.__init__(self)

    def run(self):
        self.read_acquired = self._rw_lock.enter_read_lock(self._lock_timeout)
        self.read_lock_held = self._rw_lock.is_read_lock_held
        if not self.read_acquired:
            return
        time.sleep(self._wait_timeout)
        self.value_read = self.working_list[0]
        self._rw_lock.exit_read_lock()


class TestReaderWriterLock(unittest.TestCase):

    def test_reading_before_writing(self):
        rw_lock = ReaderWriterLock()
        working_list = [1]
        writer1 = WriterThread(rw_lock, -1, 0, working_list, 2)
        writer1.start()
        writer1.join()
        self.assertTrue(writer1.write_acquired)
        self.assertEqual(working_list[0], 2)
        reader1 = ReaderThread(rw_lock, -1, 3, working_list)
        reader1.start()
        time.sleep(1)
        writer2 = WriterThread(rw_lock, -1, 0, working_list, 3)
        writer2.start()
        reader1.join()
        writer2.join()
        self.assertTrue(reader1.read_acquired)
        self.assertEqual(reader1.value_read, 2)
        self.assertTrue(writer2.write_acquired)
        self.assertEqual(working_list[0], 3)

    def test_writing_before_reading(self):
        rw_lock = ReaderWriterLock()
        working_list = [1]
        writer1 = WriterThread(rw_lock, -1, 3, working_list, 2)
        writer1.start()
        time.sleep(1)
        reader1 = ReaderThread(rw_lock, -1, 0, working_list)
        reader1.start()
        reader1.join()
        writer1.join()
        self.assertTrue(reader1.read_acquired)
        self.assertTrue(writer1.write_acquired)
        self.assertEqual(reader1.value_read, 2)
        self.assertEqual(working_list[0], 2)

    def test_write_starvation(self):
        rw_lock = ReaderWriterLock()
        working_list = [1]
        reader1 = ReaderThread(rw_lock, -1, 5, working_list)
        reader1.start()
        time.sleep(1)
        writer1 = WriterThread(rw_lock, -1, 0, working_list, 2)
        writer1.start()
        time.sleep(1)
        reader2 = ReaderThread(rw_lock, -1, 0, working_list)
        reader2.start()
        reader1.join()
        reader2.join()
        writer1.join()
        self.assertEqual(reader1.value_read, 1)
        self.assertEqual(reader2.value_read, 2)
        self.assertEqual(working_list[0], 2)

    def test_enter_timeout(self):
        rw_lock = ReaderWriterLock()
        working_list = [1]
        writer1 = WriterThread(rw_lock, -1, 3, working_list, 2)
        writer1.start()
        time.sleep(1)
        reader1 = ReaderThread(rw_lock, 0.1, 0, working_list)
        reader1.start()
        writer2 = WriterThread(rw_lock, 0.1, 0, working_list, 3)
        writer2.start()
        reader1.join()
        writer2.join()
        writer1.join()
        self.assertTrue(writer1.write_acquired)
        self.assertFalse(reader1.read_acquired)
        self.assertFalse(writer2.write_acquired)
        self.assertEqual(working_list[0], 2)

    def test_waiting_writer_timeout(self):
        rw_lock = ReaderWriterLock()
        working_list = [1]
        reader1 = ReaderThread(rw_lock, -1, 5, working_list)
        reader1.start()
        time.sleep(1)
        writer1 = WriterThread(rw_lock, -1, 0, working_list, 2)
        writer1.start()
        time.sleep(1)
        reader2 = ReaderThread(rw_lock, 0.1, 0, working_list)
        reader2.start()
        reader1.join()
        reader2.join()
        writer1.join()
        self.assertTrue(reader1.read_acquired)
        self.assertFalse(reader2.read_acquired)
        self.assertTrue(writer1.write_acquired)
        self.assertEqual(reader1.value_read, 1)
        self.assertEqual(working_list[0], 2)

    def test_properties(self):
        rw_lock = ReaderWriterLock()
        working_list = [1]
        self.assertEqual(rw_lock.current_read_count, 0)
        reader1 = ReaderThread(rw_lock, -1, 3, working_list)
        reader1.start()
        time.sleep(1)
        self.assertFalse(rw_lock.is_read_lock_held)
        self.assertEqual(rw_lock.current_read_count, 1)
        writer1 = WriterThread(rw_lock, -1, 3, working_list, 2)
        writer1.start()
        time.sleep(1)
        self.assertFalse(rw_lock.is_write_lock_held)
        reader1.join()
        writer1.join()
        self.assertTrue(reader1.read_lock_held)
        self.assertTrue(writer1.write_lock_held)

    def test_upgrade_read_to_write_lock(self):
        rw_lock = ReaderWriterLock()
        rw_lock.enter_read_lock()
        self.assertTrue(rw_lock.is_read_lock_held)
        rw_lock.upgrade_read_to_write_lock()
        self.assertTrue(rw_lock.is_write_lock_held)
        self.assertFalse(rw_lock.is_read_lock_held)
        rw_lock.downgrade_write_to_read_lock()
        self.assertTrue(rw_lock.is_read_lock_held)
        self.assertFalse(rw_lock.is_write_lock_held)
