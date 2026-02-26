OUT = menu.bin m3nu.bin
SRC = main.a65

all: $(OUT)

DEPS = memmap.i65 dma.i65 stack.i65 data.i65 header.a65 reset.a65 \
       anim.a65 ui.a65 common.a65 pad.a65 filesel.a65 time.a65 \
       menu.a65 menudata.a65 sysinfo.a65 \
       dma.a65 font.a65 palette.a65 const.a65

menu.bin: $(SRC) $(DEPS)
	64tass --m65816 -b -o $@ $(SRC) 2>&1 | tee build.log
	@echo "---"
	@ls -la menu.bin 2>/dev/null || true

m3nu.bin: menu.bin
	cp menu.bin m3nu.bin

clean:
	rm -f menu.bin m3nu.bin build.log

.PHONY: all clean
