// Pre-script: add GBA RAM/IO blocks so references into them resolve.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.mem.Memory;

public class AddGbaRam extends GhidraScript {
    @Override
    protected void run() throws Exception {
        Memory mem = currentProgram.getMemory();
        String[][] blocks = {
            {"EWRAM", "0x02000000", "0x40000"},
            {"IWRAM", "0x03000000", "0x8000"},
            {"IO", "0x04000000", "0x400"},
        };
        for (String[] b : blocks) {
            mem.createUninitializedBlock(b[0], toAddr(b[1]), Long.decode(b[2]), false)
               .setWrite(true);
        }
        // Thumb entry: ROM header branches to ARM crt0; mark a Thumb hint for code at ReadKeys.
        println("RAM blocks added");
    }
}
