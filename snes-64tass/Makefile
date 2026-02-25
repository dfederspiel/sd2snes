OUT = menu.bin m3nu.bin
SRC = main.a65

all: $(OUT)

menu.bin: $(SRC) memmap.i65 dma.i65 header.a65 reset.a65
	64tass --m65816 -b -o $@ $(SRC) 2>&1 | tee build.log
	@echo "---"
	@ls -la menu.bin 2>/dev/null || true

m3nu.bin: menu.bin
	cp menu.bin m3nu.bin

clean:
	rm -f menu.bin m3nu.bin build.log

.PHONY: all clean
