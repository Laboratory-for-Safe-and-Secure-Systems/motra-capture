from capcon.util.payload import genPayload, GenericPayload


def genCommand(options: list[str], runtime: str) -> str:
    opts = ",".join(options)
    return f"perf stat -e {opts} -I 100 -j -o cap.json -a sleep {runtime}"


default_options = [
    "branch-misses",
    "bus-cycles",
    "cache-misses",
    "cache-references",
    "cpu-cycles",
    "instructions",
]

base_cache_options = [
    "L1-dcache-load-misses",
    "L1-icache-load-misses",
    "L1-dcache-store-misses",
    "L1-dcache-stores",
    "L1-dcache-loads",
    "L1-icache-loads",
    "dTLB-load-misses",
    "dTLB-store-misses",
    "iTLB-load-misses",
    "branch-load-misses",
    "branch-loads",
    "node-loads",
    "node-stores",
]

branch_options = [
    "br_immed_spec",
    "br_indirect_spec",
    "br_mis_pred",
    "br_pred",
    "br_return_spec",
]

bus_options = [
    "bus_access",
    "bus_access_normal",
    "bus_access_not_shared",
    "bus_access_periph",
    "bus_access_rd",
    "bus_access_shared",
    "bus_access_wr",
    "bus_cycles",
    "cpu_cycles",
]

cache_options = [
    "l1d_cache",
    "l1d_cache_inval",
    "l1d_cache_rd",
    "l1d_cache_refill",
    "l1d_cache_refill_rd",
    "l1d_cache_refill_wr",
    "l1d_cache_wb",
    "l1d_cache_wb_clean",
    "l1d_cache_wb_victim",
    "l1d_cache_wr",
    "l1d_tlb_refill",
    "l1d_tlb_refill_rd",
    "l1d_tlb_refill_wr",
    "l1i_cache",
    "l1i_cache_refill",
    "l1i_tlb_refill",
    "l2d_cache",
    "l2d_cache_inval",
    "l2d_cache_rd",
    "l2d_cache_refill",
    "l2d_cache_refill_rd",
    "l2d_cache_refill_wr",
    "l2d_cache_wb",
    "l2d_cache_wb_clean",
    "l2d_cache_wb_victim",
    "l2d_cache_wr",
]

exception_options = ["exc_dabort", "exc_svc", "exc_taken", "exc_irq", "exc_pabort"]

# these tend to read 0, needs more testing to find out if these are usefull
unususal_exception_options = [
    "exc_fiq",
    "exc_hvc",
    "exc_smc",
    "exc_trap_dabort",
    "exc_trap_fiq",
    "exc_trap_irq",
    "exc_trap_other",
    "exc_trap_pabort",
    "exc_undef",
    "memory_error",
]

instruction_options = [
    "ase_spec",
    "cid_write_retired",
    "crypto_spec",
    "dmb_spec",
    "dp_spec",
    "dsb_spec",
    "exc_return",
    "inst_retired",
    "inst_spec",
    "isb_spec",
    "ld_spec",
    "ldrex_spec",
    "ldst_spec",
    "pc_write_spec",
    "rc_ld_spec",
    "rc_st_spec",
    "st_spec",
    "strex_fail_spec",
    "strex_pass_spec",
    "sw_incr",
    "ttbr_write_retired",
    "vfp_spec",
]

memory_options = [
    "mem_access",
    "mem_access_rd",
    "mem_access_wr",
    "unaligned_ld_spec",
    "unaligned_ldst_spec",
    "unaligned_st_spec",
]


# some perf examples for how to configure the different available hardware units:
# perf stat -d -j -e cache-references,cache-misses,cycles,instructions sleep 60
# perf stat -I 100 -j -o cap.json -a sleep 60
# perf stat -d -I 100 -a sleep 10 # detailed stats for general stuff...
# perf stat -e

perf_stat_payloads: list[GenericPayload] = []
perf_stat_payloads.append(
    genPayload(
        command=genCommand(default_options, 300),
        description="perf stat default",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(exception_options, 300),
        description="perf stat exception 1",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)


perf_stat_payloads.append(
    genPayload(
        command=genCommand(unususal_exception_options[0:6], 300),
        description="perf stat exception 2",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(unususal_exception_options[6:], 300),
        description="perf stat exception 3",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)


perf_stat_payloads.append(
    genPayload(
        command=genCommand(branch_options, 300),
        description="perf stat branch",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(memory_options, 300),
        description="perf stat memory",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)


perf_stat_payloads.append(
    genPayload(
        command=genCommand(instruction_options[0:6], 300),
        description="perf stat instruction 1",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(instruction_options[6:12], 300),
        description="perf stat instruction 2",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(instruction_options[12:18], 300),
        description="perf stat instruction 3",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(instruction_options[18:], 300),
        description="perf stat instruction 4",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)


perf_stat_payloads.append(
    genPayload(
        command=genCommand(base_cache_options[0:3], 300),
        description="perf stat base cache 1",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(base_cache_options[3:6], 300),
        description="perf stat base cache 2",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(base_cache_options[6:9], 300),
        description="perf stat base cache 3",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(base_cache_options[9:], 300),
        description="perf stat base cache 4",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)


perf_stat_payloads.append(
    genPayload(
        command=genCommand(cache_options[0:6], 300),
        description="perf stat cache 1",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(cache_options[6:12], 300),
        description="perf stat cache 2",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(cache_options[12:18], 300),
        description="perf stat cache 3",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(cache_options[18:24], 300),
        description="perf stat cache 4",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)

perf_stat_payloads.append(
    genPayload(
        command=genCommand(cache_options[24:], 300),
        description="perf stat cache 5",
        limits="302s",
        offset="500ms",
        payload_type="capture",
    )
)
