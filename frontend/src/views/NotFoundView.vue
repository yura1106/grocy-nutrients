<template>
  <div class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10 text-center">
        <h2 class="text-3xl font-extrabold text-gray-900 mb-6">404</h2>
        <p class="text-gray-600 mb-6">Page not found</p>
        <div>
          <router-link
            to="/"
            class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-xs text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Go back home
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template> 