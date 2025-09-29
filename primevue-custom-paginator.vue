<template>
  <div class="paginator">
    <button :disabled="currentPage === 1" @click="selectPreviousRange">
      Previous
    </button>
    <span
      v-for="page in pages"
      :key="page"
      :class="{ selected: page === currentPage }"
      @click="selectPage(page)"
      >{{ page }}</span
    >
    <button :disabled="currentPage === totalPages" @click="selectNextRange">
      Next
    </button>
  </div>
</template>

<script>
export default {
  props: {
    totalPages: {
      type: Number,
      required: true
    },
    rowsPerPage: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      currentPage: 1,
      selectedRange: [1]
    };
  },
  computed: {
    pages() {
      const range = [];
      if (this.totalPages <= 5) {
        for (let i = 1; i <= this.totalPages; i++) {
          range.push(i);
        }
      } else {
        let start = Math.max(1, this.currentPage - 2);
        let end = Math.min(this.totalPages, this.currentPage + 2);
        if (this.currentPage < 3) {
          end = 5;
        } else if (this.currentPage > this.totalPages - 2) {
          start = this.totalPages - 4;
        }
        for (let i = start; i <= end; i++) {
          range.push(i);
        }
      }
      return range;
    }
  },
  methods: {
    selectPage(page) {
      this.currentPage = page;
    },
    selectPreviousRange() {
      let newRange = [];
      if (this.selectedRange.length > 1) {
        for (let i = 0; i < this.selectedRange.length - 1; i++) {
          newRange.push(this.selectedRange[i]);
        }
      } else {
        newRange = [1];
      }
      this.currentPage = Math.max(newRange[0], 1);
    },
    selectNextRange() {
      let newRange = [...this.selectedRange];
      if (this.selectedRange[this.selectedRange.length - 1] < this.totalPages) {
        for (let i = 0; i < this.selectedRange.length; i++) {
          newRange.push(this.selectedRange[i] + 1);
        }
      } else {
        newRange = [Math.max(newRange[0], 1)];
      }
      this.currentPage = Math.min(
        newRange[newRange.length - 1],
        this.totalPages
      );
    }
  },
  created() {
    if (this.$attrs.currentPage) {
      this.currentPage = this.$attrs.currentPage;
    }
  }
};
</script>

<style scoped>
.paginator {
  display: flex;
  align-items: center;
}

.paginator button,
.paginator span {
  margin: 0 5px;
  cursor: pointer;
}

.selected {
  font-weight: bold;
  color: #007bff;
}
</style>
