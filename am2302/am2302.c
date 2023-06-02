#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define GPIO_BASE 0x3F200000   // for Pi 2/3/4
#define GPIOMEM_GPIO_BASE 0x0  // for Pi 2/3/4
#define BLOCK_SIZE (4 * 1024)

int main() {
  int mem_fd;
  void *gpio_map;
  volatile unsigned *gpio;

  // open /dev/gpiomem
  if ((mem_fd = open("/dev/gpiomem", O_RDWR | O_SYNC)) < 0) {
    printf("can't open /dev/gpiomem \n");
    exit(-1);
  }

  gpio_map =
      mmap(NULL,                    // Any adddress will do
           BLOCK_SIZE,              // Map length
           PROT_READ | PROT_WRITE,  // Enable reading & writing to mapped memory
           MAP_SHARED,              // Shared with other processes
           mem_fd,                  // File to map
           GPIOMEM_GPIO_BASE        // Offset to GPIO peripheral
      );

  close(mem_fd);  // can close /dev/gpiomem now

  if (gpio_map == MAP_FAILED) {
    printf("mmap error %p\n", gpio_map);
    exit(-1);
  }

  // Always use volatile pointer!
  gpio = (volatile unsigned *)gpio_map;

  // Set a pull up resistor on pin 19
  *(gpio + 37) = 2;
  usleep(1);
  *(gpio + 38) = 1 << 19;
  usleep(1);
  *(gpio + 37) = 0;
  *(gpio + 38) = 0;

  // Set high by writing bit 19 in output set register 0
  *(gpio + 7) = 1 << 19;  // Set GPIO19 high (zeros have no effect)

  // Each function select register controls 10 pins. Each pin has 3 bits to
  // control, and we want to ensure we set pin 19's bit to 001.
  *(gpio + 1) &= ~(7 << ((19 % 10) * 3));  // clear bits
  *(gpio + 1) |= 1 << ((19 % 10) * 3);     // set as output
  usleep(5000);

  // Set low by writing bit 19 in output clear register 0
  *(gpio + 10) = 1 << 19;  // Set GPIO19 low (zeros have no effect)
  usleep(5000);
  *(gpio + 7) = 1 << 19;  // Set GPIO19 high (zeros have no effect)
  // Clear GPIO19 bits in Function Select Register to set as input
  *(gpio + 1) &= ~(7 << ((19 % 10) * 3));

  // Configure to detect falling edges on pin 19
  // Write to GPFEN0 register
  *(gpio + 22) |= (1 << 19);

  // Start polling
  struct timespec delay = {0, 10000};
  struct timespec edgeTimes[42];
  int idx;
  struct timespec start;
  clock_gettime(CLOCK_MONOTONIC, &start);
  while (1) {
    if (*(gpio + 16) & (1 << 19)) {  // If event detected
      // Clear event
      *(gpio + 16) = (1 << 19);
      clock_gettime(CLOCK_MONOTONIC, &edgeTimes[idx]);
      idx++;
      if (idx >= 42) {
        break;
      }
    }
    nanosleep(&delay, NULL);
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    if ((now.tv_sec - start.tv_sec) > 2) {
      break;
    }
  }
  printf("Found %d falling edges\n", idx);
  printf("Timestamps:\n");
  for (int i = 0; i < 42; i++) {
    printf("%lld.%.9ld\n", (long long)edgeTimes[i].tv_sec,
           edgeTimes[i].tv_nsec);
  }

  for (int i = 2; i < 42; i++) {
    printf("%lld.%.9ld\n",
           (long long)edgeTimes[i].tv_sec - (long long)edgeTimes[i - 1].tv_sec,
           edgeTimes[i].tv_nsec - edgeTimes[i - 1].tv_nsec);
  }
  //   *(gpio + 7) = 1 << 19;   // Set GPIO19 high

  return 0;
}
