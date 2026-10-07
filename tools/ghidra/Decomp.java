// Decompile functions listed in env DECOMP_ADDRS (comma-separated hex) to DECOMP_OUT.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.Function;
import java.io.*;

public class Decomp extends GhidraScript {
    @Override
    protected void run() throws Exception {
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        try (PrintWriter pw = new PrintWriter(new FileWriter(System.getenv("DECOMP_OUT")))) {
            for (String s : System.getenv("DECOMP_ADDRS").split(",")) {
                Function f = getFunctionContaining(toAddr(Long.decode(s.trim())));
                if (f == null) { pw.println("// no function at " + s); continue; }
                DecompileResults r = di.decompileFunction(f, 60, monitor);
                pw.println("// ===== " + f.getEntryPoint() + " " + f.getName());
                pw.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// failed: " + r.getErrorMessage());
            }
        }
    }
}
