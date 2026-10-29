"""Learning resources: revision notes, references and class materials.

Every external link here was opened and checked before it was added. Video
titles are the titles shown on YouTube. Nothing is claimed to be included
unless the file actually exists in class_notes/.
"""

from pathlib import Path

CLASS_NOTES_DIR = Path(__file__).resolve().parent.parent / "class_notes"
ALLOWED_EXTENSIONS = {".pdf", ".ppt", ".pptx"}

MIME = {
    ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def list_class_materials(folder: Path | str = CLASS_NOTES_DIR) -> list[Path]:
    """PDF/PPT/PPTX files placed in the class-notes folder, sorted by name.

    Returns an empty list when the folder doesn't exist. Hidden files and other
    file types are ignored.
    """
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.iterdir()
                   if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in ALLOWED_EXTENSIONS),
                  key=lambda p: p.name.lower())


REVISION_NOTES = [
    ("Deadlock",
     "A set of processes in which each one waits for a resource held by another process in the same set. "
     "None can proceed, so none will release what it holds."),
    ("Coffman conditions",
     "Mutual exclusion, hold and wait, no preemption, circular wait. All four are necessary; "
     "remove any one and deadlock is impossible."),
    ("Need",
     "Need = Max − Allocation: what a process may still request before it finishes."),
    ("Safe state",
     "There is an order (a safe sequence) in which every process can get its remaining Need, finish and "
     "release its resources."),
    ("Unsafe ≠ deadlocked",
     "Unsafe means completion can't be guaranteed. Deadlocked means processes are already blocked on each "
     "other. Every deadlocked state is unsafe, not the other way round."),
    ("Banker's request check",
     "Request > Need → invalid. Request > Available → wait. Otherwise allocate on a trial copy and run the "
     "safety algorithm: safe → grant, unsafe → deny and roll back."),
    ("Avoidance vs detection",
     "Avoidance (Banker's) uses maximum claims and acts before each grant. Detection uses current requests "
     "and finds deadlocks that already exist. Banker's never detects an existing deadlock."),
    ("Cycles",
     "Single-instance resources: a cycle in the wait-for graph proves deadlock. Multiple instances: a cycle "
     "is necessary but not sufficient; run the detection algorithm."),
    ("Recovery",
     "Abort deadlocked processes (one at a time, or all), or preempt resources with rollback. Choose victims "
     "to minimise lost work."),
    ("Ignorance",
     "Do nothing and let a user or administrator clear the rare deadlock. Deadlocks still happen; this only "
     "skips the cost of handling them."),
]

# (title, source/channel, url, topic). Titles and channels as shown on YouTube.
VIDEOS = [
    ("Deadlock Prevention | L 22 | Operating System | GATE 2022 CSE", "Unacademy Computer Science",
     "https://www.youtube.com/live/wIqn3n2ATQ0", "Prevention"),
    ("Operating System Deadlock Avoidance Algorithm Demo using Role Play by BVRIT, Narsapur Students",
     "vijaymantri", "https://www.youtube.com/watch?v=JTgP3mblSB4", "Avoidance"),
    ("L-4.5: Deadlock Avoidance Banker's Algorithm with Example", "Gate Smashers",
     "https://youtu.be/7gMLNiEz3nw", "Banker's Algorithm"),
    ("Deadlock Recovery in Operating System | GATE CSE", "THE GATEHUB",
     "https://youtu.be/LTr1a643FiQ", "Detection & recovery"),
    ("L5.26: Deadlock Ignorance | Ostrich Algorithm in Deadlock in OS", "Success GATEway",
     "https://youtu.be/HP1JuTbJMN4", "Ignorance"),
]

VIDEO_ATTRIBUTION = ("Video list curated by Vivek Sanap in the team's reference repository "
                     "[Viveksanap18/Deadlock](https://github.com/Viveksanap18/Deadlock).")

# (citation, url, what it covers)
READINGS = [
    ("A. Silberschatz, P. B. Galvin, G. Gagne. Operating System Concepts, 10th ed., Wiley, 2018. Chapter 8: Deadlocks.",
     "https://www.os-book.com/OS10/", "Course textbook treatment of all four strategies, Banker's and detection."),
    ("R. H. Arpaci-Dusseau, A. C. Arpaci-Dusseau. Operating Systems: Three Easy Pieces. Chapter 32: Common "
     "Concurrency Problems (free PDF).",
     "https://pages.cs.wisc.edu/~remzi/OSTEP/threads-bugs.pdf", "Deadlock in real multithreaded code; lock ordering."),
    ("E. G. Coffman, M. J. Elphick, A. Shoshani. System Deadlocks. ACM Computing Surveys 3(2), 1971.",
     "https://doi.org/10.1145/356586.356588", "Origin of the four necessary conditions."),
    ("E. W. Dijkstra. EWD108: Een algorithme ter voorkoming van de dodelijke omarming (in Dutch), c. 1964.",
     "https://www.cs.utexas.edu/~EWD/ewd01xx/EWD108.PDF", "Original description of the Banker's Algorithm."),
    ("A. S. Tanenbaum, H. Bos. Modern Operating Systems, 4th ed., Pearson, 2014. Chapter 6: Deadlocks.",
     None, "Source of the \"ostrich algorithm\" name and discussion."),
]
