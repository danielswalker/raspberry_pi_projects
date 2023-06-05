#include <fcntl.h>
#include <stdint.h>
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
  printf("Mem mapped\n");

  // Always use volatile pointer!
  gpio = (volatile unsigned *)gpio_map;

  // Set a pull up resistor on pin 19
  *(gpio + 37) = 2;
  usleep(10);
  *(gpio + 38) = 1 << 19;
  usleep(10);
  *(gpio + 37) = 0;
  *(gpio + 38) = 0;
  printf("Set pull up\n");

  // Set high by writing bit 19 in output set register 0
  *(gpio + 7) = 1 << 19;  // Set GPIO19 high (zeros have no effect)
  printf("Preset pin 19 to be high\n");

  // Each function select register controls 10 pins. Each pin has 3 bits to
  // control, and we want to ensure we set pin 19's bit to 001.
  *(gpio + 1) &= ~(7 << ((19 % 10) * 3));  // clear bits
  *(gpio + 1) |= 1 << ((19 % 10) * 3);     // set as output
  printf("Set pin to be an output\n");

  // Set pin 19 low by writing bit 19 in output clear register 0
  *(gpio + 10) = 1 << 19;  // Set GPIO19 low (zeros have no effect)
  printf("Set low\n");

  // Wait long enough to signal the AM2302
  usleep(2000);

  // Clear GPIO19 bits in Function Select Register to set as input
  *(gpio + 1) &= ~(7 << ((19 % 10) * 3));

  // EVENT DETECTION METHOD - this approach would occasionally freeze Raspberry
  // pi; work around is likely using an overlay to turn off GPIO interrupts
  // Configure to detect falling edges on pin 19
  // *(gpio + 22) |= (1 << 19); // Write to GPFEN0 register
  // period between checks of the event register
  // struct timespec delay = {0, 1000};

  // track falling edge times in a buffer
  struct timespec edgeTimes[42];
  int edgeIdx = 0;

  // start time
  struct timespec start;
  clock_gettime(CLOCK_MONOTONIC, &start);

  // look for falling edges
  char pinState = 1;
  char prevPinState = 1;
  while (1) {
    // POLL FOR FALLING EDGE METHOD
    pinState = (*(gpio + 13) & (1 << 19)) != 0;
    if (prevPinState == 1 && pinState == 0) {
      // falling edge
      clock_gettime(CLOCK_MONOTONIC, &edgeTimes[edgeIdx]);
      edgeIdx++;
      if (edgeIdx > 41) {
        break;
      }
    }
    prevPinState = pinState;

    // EVENT DETECTION METHOD - this approach would occasionally freeze
    // if (*(gpio + 16) & (1 << 19)) {  // If event detected
    //   // Clear event
    //   *(gpio + 16) = (1 << 19);
    //   clock_gettime(CLOCK_MONOTONIC, &edgeTimes[edgeIdx]);
    //   edgeIdx++;
    //   if (edgeIdx > 41) {
    //     break;
    //   }
    // }
    // nanosleep(&delay, NULL);

    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    if ((now.tv_sec - start.tv_sec) > 2) {
      printf("Timed out!\n");
      if (munmap((void *)gpio, BLOCK_SIZE) == -1) {
        printf("Failed to unmap memory\n");
      }
      exit(-1);
    }
  }

  // EVENT DETECTION METHOD - this approach would occasionally freeze
  // turn off edge detection
  // *(gpio + 22) = 0;

  // unmap our memory to clean up
  if (munmap((void *)gpio, BLOCK_SIZE) == -1) {
    printf("Failed to unmap memory\n");
  }

  printf("Found %d falling edges\n", edgeIdx);

  // expect 42 falling edges - the first two are part of AM2302 signaling, 40
  // are part of the bit payload
  if (edgeIdx < 42) {
    printf("Did not find enough edges\n");
    exit(-1);
  }

  // the MSB is bit 0, it should end up as MSB in byte[4]
  uint8_t payloadBytes[5] = {0};
  for (int bit = 0; bit < 40; bit++) {
    char pulseEndIndex = bit + 2;
    if (pulseEndIndex >= edgeIdx) {
      break;
    }
    // the MSB is the time between pulse 2 and 1 (0-indexed)
    long long seconds = (long long)(edgeTimes[pulseEndIndex].tv_sec -
                                    edgeTimes[pulseEndIndex - 1].tv_sec);
    long nanoseconds =
        edgeTimes[pulseEndIndex].tv_nsec - edgeTimes[pulseEndIndex - 1].tv_nsec;

    if (nanoseconds < 0) {
      seconds--;
      nanoseconds += 1000000000;
    }

    // short pulses should be ~75 ms, long pulses ~120 ms
    if (seconds > 0 || nanoseconds / 1000 > 100) {
      payloadBytes[4 - bit / 8] <<= 1;
      payloadBytes[4 - bit / 8] |= 1;
    } else {
      payloadBytes[4 - bit / 8] <<= 1;
    }

    // printf("%ld\n", nanoseconds / 1000);
  }
  if (payloadBytes[0] != (0xFF & (payloadBytes[1] + payloadBytes[2] +
                                  payloadBytes[3] + payloadBytes[4]))) {
    printf("Checksum failed!\n");
    exit(-1);
  }

  uint16_t humidityInt;
  humidityInt = (payloadBytes[4] << 8) + payloadBytes[3];

  uint16_t tempMagnitudeInt;
  tempMagnitudeInt = ((payloadBytes[2] & 0x7F) << 8) + payloadBytes[1];

  char tempSignBit;
  tempSignBit = (payloadBytes[2] & 0x7F) != 0;

  float humidityPercent;
  humidityPercent = humidityInt / 10.0;

  float temperatureF;
  temperatureF = tempMagnitudeInt / 10.0 * 9.0 / 5.0 + 32.0;
  if (tempSignBit) {
    temperatureF *= -1.0;
  }

  printf("%f, %f\n", humidityPercent, temperatureF);
  return 0;
}
