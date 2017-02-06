import threading


class ReaderWriterLock:
    """Represents a lock that is used to manage access to a resource, \
    allowing multiple threads for reading or exclusive access for writing."""

    def __init__(self):
        self._reading_threads = set()
        self._writing_thread = 0
        self._writer_wait_count = 0
        self._read_lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._sync_lock = threading.RLock()
        self._writer_waiting_event = threading.Event()
        self._writer_waiting_event.set()  # set means no writer is waiting

    @property
    def current_read_count(self) -> int:
        """Gets the total number of unique threads that have entered the lock in read mode."""
        with self._sync_lock:
            return len(self._reading_threads)

    @property
    def is_read_lock_held(self) -> bool:
        """Gets a value that indicates whether the current thread has entered the lock in read mode."""
        with self._sync_lock:
            return threading.get_ident() in self._reading_threads

    @property
    def is_write_lock_held(self) -> bool:
        """Gets a value that indicates whether the current thread has entered the lock in write mode."""
        with self._sync_lock:
            return threading.get_ident() == self._writing_thread

    def enter_read_lock(self, timeout: float = -1) -> bool:
        """Tries to enter the lock in read mode."""
        if self.is_read_lock_held or \
           self.is_write_lock_held or \
           not(self._writer_waiting_event.wait(None if timeout == -1 else timeout)) or \
           not(self._read_lock.acquire(True, timeout)):
            return False

        self._sync_lock.acquire()
        if self.current_read_count == 0:
            self._sync_lock.release()  # release before waiting on write lock
            if not(self._write_lock.acquire(True, timeout)):
                self._read_lock.release()
                return False
            with self._sync_lock:
                self._reading_threads.add(threading.get_ident())
        else:
            self._reading_threads.add(threading.get_ident())
            self._sync_lock.release()

        self._read_lock.release()
        return True

    def upgrade_read_to_write_lock(self, timeout: float = -1) -> bool:
        return self.enter_write_lock(timeout, True)

    def enter_write_lock(self, timeout: float = -1, upgrade_read: bool = False) -> bool:
        """Tries to enter the lock in write mode."""
        with self._sync_lock:
            if self.is_write_lock_held:
                return False

            if upgrade_read:
                if self.is_read_lock_held:
                    self.exit_read_lock()  # upgrade to write lock
                else:
                    return False  # read lock is not held, can't upgrade

            self._writer_wait_count += 1
            if self._writer_wait_count == 1:
                self._writer_waiting_event.clear()

        write_lock_acquired = self._write_lock.acquire(True, timeout)

        with self._sync_lock:
            self._writer_wait_count -= 1
            if self._writer_wait_count == 0:
                self._writer_waiting_event.set()

            if not write_lock_acquired:
                return False

            self._writing_thread = threading.get_ident()
            return True

    def exit_read_lock(self):
        """Exits read mode."""
        with self._read_lock:
            with self._sync_lock:
                if self.is_read_lock_held:
                    self._reading_threads.remove(threading.get_ident())
                    if self.current_read_count == 0:
                        self._write_lock.release()

    def downgrade_write_to_read_lock(self):
        self.exit_write_lock(True)

    def exit_write_lock(self, downgrade_to_read: bool = False):
        """Exits write mode."""
        with self._sync_lock:
            if self.is_write_lock_held:
                self._writing_thread = 0
                self._write_lock.release()

            if downgrade_to_read and not self.is_read_lock_held:
                self.enter_read_lock()
