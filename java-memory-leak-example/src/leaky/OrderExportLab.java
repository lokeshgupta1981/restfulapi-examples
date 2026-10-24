import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

public class OrderExportLab {
    private static final int PAYLOAD_BYTES = 256 * 1024;
    private static final Map<Long, ExportResult> IN_FLIGHT = new HashMap<>();
    private static long completed;
    private static long checksum;

    private record ExportResult(long jobId, byte[] payload) {}

    private static void exportOrder(long jobId) {
        byte[] payload = new byte[PAYLOAD_BYTES];
        payload[0] = (byte) jobId;
        ExportResult result = new ExportResult(jobId, payload);
        IN_FLIGHT.put(jobId, result);
        try {
            checksum += Byte.toUnsignedInt(result.payload()[0]);
            completed++;
        } finally {
            // The completed export is accidentally left in IN_FLIGHT.
        }
    }

    private static void printStatus() {
        long payloadBytes = (long) IN_FLIGHT.size() * PAYLOAD_BYTES;
        System.out.printf(Locale.ROOT,
                "completed=%d tracked=%d retainedPayloadMiB=%.2f checksum=%d%n",
                completed, IN_FLIGHT.size(), payloadBytes / 1048576.0, checksum);
        System.out.flush();
    }

    public static void main(String[] args) throws Exception {
        System.out.println("OrderExportLab pid=" + ProcessHandle.current().pid());
        System.out.println("Commands  batch <1-256> | status | exit");
        printStatus();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.trim().split("\\s+");
                if (parts[0].equals("exit")) {
                    break;
                } else if (parts[0].equals("status")) {
                    printStatus();
                } else if (parts[0].equals("batch") && parts.length == 2) {
                    try {
                        int count = Integer.parseInt(parts[1]);
                        if (count < 1 || count > 256) {
                            throw new IllegalArgumentException();
                        }
                        for (int i = 0; i < count; i++) {
                            exportOrder(completed + 1);
                        }
                        printStatus();
                    } catch (IllegalArgumentException ex) {
                        System.out.println("Use batch with an integer from 1 through 256.");
                    }
                } else {
                    System.out.println("Commands  batch <1-256> | status | exit");
                }
                System.out.flush();
            }
        }
    }
}
