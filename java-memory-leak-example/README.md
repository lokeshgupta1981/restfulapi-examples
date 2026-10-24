Source code for the article [How to Debug a Java Memory Leak Step by Step](https://howtodoinjava.com/wp-admin/post.php?post=44436&action=edit).

# Order export memory-leak lab

This deliberately broken program tracks in-flight exports but never removes completed ones.
Use it only as a local diagnostic exercise. It does not process real order data or call services.

Requires a HotSpot JDK with javac and jcmd. Verified version and captured results are recorded in the article evidence directory.

From this project directory, compile and start the leaking version in terminal one.

```bash
mkdir out
mkdir artifacts
javac -d out src/leaky/OrderExportLab.java
java -Xms128m -Xmx128m -XX:+UseSerialGC -Xlog:gc:file=artifacts/leaky-gc.log:uptime,level,tags -cp out OrderExportLab
```

Enter `batch 64` three times, collecting diagnostics from terminal two after each batch.
The program prints its process ID. Replace `12345` with that ID.

```bash
jcmd 12345 GC.run
jcmd 12345 GC.heap_info
jcmd 12345 GC.class_histogram
jcmd 12345 GC.heap_dump artifacts/leaky.hprof
```

Use an absolute destination path if diagnosing a JVM started in another directory.
Exit terminal one's application before recompiling.

```bash
javac -d out src/fixed/OrderExportLab.java
java -Xms128m -Xmx128m -XX:+UseSerialGC -Xlog:gc:file=artifacts/fixed-gc.log:uptime,level,tags -cp out OrderExportLab
```

Repeat the same three batches and diagnostics with the new process ID. Save the fixed dump as `artifacts/fixed.hprof`.
The fixed source removes the tracking entry in a finally block. Completed counts and checksums remain identical; tracked completed exports stay at zero.

GC requests and heap inspections are deliberately used at idle checkpoints in this local lab. They can pause a real service. Do not use this command sequence as a production monitoring loop.
