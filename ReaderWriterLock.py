import threading


class ReaderWriterLock:
    """Represents a lock that is used to manage access to a resource, \
    allowing multiple threads for reading or exclusive access for writing."""

    def __init__(self):
        self._reading_threads = set()
        self._writing_thread = 0
        self._read_lock = threading.RLock()
        self._write_lock = threading.RLock()
        self._sync_lock = threading.RLock()

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
        """	Gets a value that indicates whether the current thread has entered the lock in write mode."""
        with self._sync_lock:
            return threading.get_ident() == self._writing_thread

    def enter_read_lock(self, timeout: float = None) -> bool:
        """Tries to enter the lock in read mode."""
        if self.is_read_lock_held or not(self._read_lock.acquire(True, timeout)):
            return False

        self._sync_lock.acquire()
        if len(self._reading_threads) == 0:
            self._sync_lock.release()  # release before waiting on writing lock
            if not(self._write_lock.acquire(True, timeout)):
                self._read_lock.release()
                return False
            else:
                self._reading_threads.add(threading.get_ident())
        else:
            self._reading_threads.add(threading.get_ident())
            self._sync_lock.release()

        self._read_lock.release()
        return True

    def enter_write_lock(self, timeout: float = None) -> bool:
        """Tries to enter the lock in write mode."""
        if self.is_write_lock_held or not(self._write_lock.acquire(True, timeout)):
            return False

        with self._sync_lock:
            self._writing_thread = threading.get_ident()
            return True

    def exit_read_lock(self):
        """Exits read mode."""
        if not self.is_read_lock_held:
            return

        with self._read_lock:
            with self._sync_lock:
                self._reading_threads.remove(threading.get_ident())
                if len(self._reading_threads) == 0:
                    self._write_lock.release()

    def exit_write_lock(self):
        """Exits write mode."""
        with self._sync_lock:
            if self.is_write_lock_held:
                self._writing_thread = 0
                self._write_lock.release()
