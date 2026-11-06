obj-m += isox_watermark.o
ccflags-y += -Werror

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD  := $(shell pwd)
all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules
clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
