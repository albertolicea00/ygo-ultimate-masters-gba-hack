// Seed Thumb functions: every BL target in ROM whose first halfword is push {..., lr}.
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.program.model.address.*;
import ghidra.program.model.lang.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.listing.*;
import java.math.BigInteger;
import java.util.TreeSet;

public class SeedThumb extends GhidraScript {
    @Override
    protected void run() throws Exception {
        Memory mem = currentProgram.getMemory();
        long base = 0x08000000L, end = 0x08400000L;
        byte[] buf = new byte[(int)(end - base)];
        mem.getBytes(toAddr(base), buf);
        TreeSet<Long> targets = new TreeSet<>();
        for (int i = 0; i + 4 <= buf.length; i += 2) {
            int h1 = (buf[i] & 0xff) | ((buf[i+1] & 0xff) << 8);
            int h2 = (buf[i+2] & 0xff) | ((buf[i+3] & 0xff) << 8);
            if ((h1 >> 11) == 0x1e && (h2 >> 11) == 0x1f) {
                int off = ((h1 & 0x7ff) << 12) | ((h2 & 0x7ff) << 1);
                if ((off & 0x400000) != 0) off -= 0x800000;
                long t = base + i + 4 + off;
                if (t < base || t >= end) continue;
                int o = (int)(t - base);
                int hw = (buf[o] & 0xff) | ((buf[o+1] & 0xff) << 8);
                if ((hw & 0xff00) == 0xb500) targets.add(t);
            }
        }
        println("thumb targets: " + targets.size());
        Register tmode = currentProgram.getRegister("TMode");
        ProgramContext ctx = currentProgram.getProgramContext();
        int n = 0;
        // Clear the bogus ARM-mode listing past crt0 so Thumb context can be set.
        clearListing(toAddr(base + 0x1000), toAddr(end - 1));
        int bad = 0;
        for (long t : targets) {
            Address a = toAddr(t);
            try { ctx.setValue(tmode, a, a, BigInteger.ONE); } catch (Exception e) { bad++; }
        }
        println("context conflicts: " + bad);
        AddressSet set = new AddressSet();
        for (long t : targets) set.add(toAddr(t));
        for (long t : targets) {
            Address a = toAddr(t);
            if (getInstructionAt(a) == null) {
                DisassembleCommand cmd = new DisassembleCommand(a, null, true);
                cmd.applyTo(currentProgram, monitor);
            }
            if (getFunctionAt(a) == null) { createFunction(a, null); n++; }
            if (monitor.isCancelled()) break;
        }
        println("functions created: " + n);
    }
}
